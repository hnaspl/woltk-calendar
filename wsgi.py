"""WSGI / ASGI entry point.

For development:  python wsgi.py
For production:   gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 wsgi:app
"""

# Fix zope namespace package resolution before any gevent imports.
# The system zope package may shadow user-installed zope.event.
import pkgutil as _pkgutil  # noqa: E402
import zope  # noqa: E402
zope.__path__ = _pkgutil.extend_path(zope.__path__, "zope")

from gevent import monkey  # noqa: E402
monkey.patch_all()

from app import create_app  # noqa: E402
from app.extensions import socketio  # noqa: E402

app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
