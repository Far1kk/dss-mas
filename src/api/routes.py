import os
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from src.api.handlers import (
    handle_index,
    handle_chat_sse,
    handle_feedback,
    handle_health,
)

_web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))

routes = [
    Route("/", endpoint=handle_index, methods=["GET"]),
    Route("/api/chat", endpoint=handle_chat_sse, methods=["GET"]),
    Route("/api/feedback", endpoint=handle_feedback, methods=["POST"]),
    Route("/api/health", endpoint=handle_health, methods=["GET"]),
    Mount("/static", app=StaticFiles(directory=_web_dir), name="static"),
]
