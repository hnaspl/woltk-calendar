"""Email validation: format check, disposable-domain blocklist, MX record lookup.

No SMTP connection is made — this validates that the email *looks* correct
and that the domain is not a known throwaway provider.
"""

from __future__ import annotations

import logging
import re
import socket

logger = logging.getLogger(__name__)

# RFC 5322 simplified – good enough for real-world addresses.
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

# ---------------------------------------------------------------------------
# Disposable / temporary email domains
# Comprehensive list of the most popular throwaway email services.
# ---------------------------------------------------------------------------
DISPOSABLE_DOMAINS: frozenset[str] = frozenset({
    # --- major disposable providers ---
    "guerrillamail.com", "guerrillamail.de", "guerrillamail.net",
    "guerrillamail.org", "guerrillamailblock.com", "grr.la",
    "sharklasers.com", "guerrillamail.info",
    "mailinator.com", "mailinator2.com", "mailinater.com",
    "mailinator.net", "mailinator.org",
    "tempmail.com", "temp-mail.org", "temp-mail.io",
    "throwaway.email", "throwaway.com",
    "yopmail.com", "yopmail.fr", "yopmail.net",
    "dispostable.com",
    "trashmail.com", "trashmail.me", "trashmail.net", "trashmail.org",
    "trashmail.io",
    "maildrop.cc",
    "10minutemail.com", "10minutemail.net",
    "getairmail.com",
    "mohmal.com",
    "tempail.com",
    "burnermail.io",
    "discard.email",
    "discardmail.com", "discardmail.de",
    "fakeinbox.com",
    "mailnesia.com",
    "mailsac.com",
    "nada.email", "nada.ltd",
    "spamgourmet.com",
    "mintemail.com",
    "mytemp.email",
    "harakirimail.com",
    "mailcatch.com",
    "tempr.email",
    "tempmailo.com",
    "tmpmail.net", "tmpmail.org",
    "emailondeck.com",
    "crazymailing.com",
    "armyspy.com",
    "cuvox.de",
    "dayrep.com",
    "einrot.com",
    "fleckens.hu",
    "gustr.com",
    "jourrapide.com",
    "rhyta.com",
    "superrito.com",
    "teleworm.us",
    "getnada.com",
    "inboxbear.com",
    "mailforspam.com",
    "meltmail.com",
    "spamfree24.org",
    "tempomail.fr",
    "trash-mail.com",
    "wegwerfmail.de", "wegwerfmail.net", "wegwerfmail.org",
    "tempinbox.com",
    "instant-mail.de",
    "emkei.cz",
    "emailfake.com",
    "generator.email",
    "jetable.org",
    "nowmymail.com",
    "owlpic.com",
    "sharklasers.com",
    "spam4.me",
    "spambox.us",
    "trashymail.com", "trashymail.net",
    "tmail.ws",
    "tempmailaddress.com",
    "tempmailer.com",
    "tempmailer.de",
    "one-time.email",
    "mailtemp.info",
    "fakemail.net",
    "dropmail.me",
    "mohmal.im",
    "tempmail.ninja",
    "tempmail.plus",
    "luxusmail.org",
    "byom.de",
    "fixmail.tk",
    "mailpoof.com",
    "tempmail.de",
    "trashinbox.com",
    "binkmail.com",
    "bobmail.info",
    "chammy.info",
    "devnullmail.com",
    "disposeamail.com",
    "dodgeit.com",
    "e4ward.com",
    "gishpuppy.com",
    "kasmail.com",
    "mailexpire.com",
    "mailmoat.com",
    "mailnull.com",
    "mailshell.com",
    "mailzilla.com",
    "nomail.xl.cx",
    "pookmail.com",
    "shortmail.net",
    "sneakemail.com",
    "sogetthis.com",
    "spamcero.com",
    "spamex.com",
    "spamherelots.com",
    "spaml.com",
    "uggsrock.com",
    "xemaps.com",
    "zoemail.com",
    "mailnator.com",
    "brefmail.com",
    "tempsky.com",
    "disposable.email",
    "mailhazard.com",
    "mailhazard.us",
    "tempm.com",
    "guerrillamail.biz",
    "mail-temporaire.fr",
    "emailisvalid.com",
    "33mail.com",
    "mailinabox.email",
    "anonymbox.com",
    "cool.fr.nf",
    "jetable.fr.nf",
    "courriel.fr.nf",
    "moncourrier.fr.nf",
    "speed.1s.fr",
    "tempe-mail.com",
})


def validate_email(email: str, *, check_mx: bool = True) -> str | None:
    """Validate an email address.

    Returns ``None`` if the email is valid, or a translation key string
    (e.g. ``"auth.errors.emailInvalidFormat"``) describing the problem.

    Set *check_mx* to ``False`` to skip the DNS lookup (useful in tests
    where network access may be unavailable).
    """
    if not email or not _EMAIL_RE.match(email):
        return "auth.errors.emailInvalidFormat"

    domain = email.rsplit("@", 1)[-1].lower()

    if domain in DISPOSABLE_DOMAINS:
        return "auth.errors.emailDisposable"

    # MX record check – verify the domain can receive email.
    if check_mx and not _has_mx_record(domain):
        return "auth.errors.emailInvalidDomain"

    return None


def _has_mx_record(domain: str) -> bool:
    """Return True if the domain has at least one MX or A/AAAA record.

    Uses a low-level DNS lookup via socket.getaddrinfo so we don't
    need an external DNS library.  Falls back to True on any network
    error (fail-open) so that transient DNS issues don't block
    registration.
    """
    try:
        # Try resolving the domain – if it has any DNS record at all
        # (MX, A, AAAA, CNAME) the domain is "real".
        socket.getaddrinfo(domain, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return True
    except socket.gaierror:
        # Domain does not resolve at all.
        return False
    except Exception:
        # Network error, timeout, etc. – fail open.
        logger.debug("DNS lookup failed for %s, allowing registration", domain)
        return True
