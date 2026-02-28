"""WSGI / ASGI entry point.

For development:  python wsgi.py
For production:   gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 wsgi:app
"""

from gevent import monkey  # noqa: E402
monkey.patch_all()

from app import create_app  # noqa: E402
from app.extensions import socketio  # noqa: E402

app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
