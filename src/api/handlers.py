import json
import asyncio
from datetime import datetime, timezone
from starlette.requests import Request
from starlette.responses import JSONResponse, FileResponse
from sse_starlette.sse import EventSourceResponse
from src.api.schemas import ChatRequest, FeedbackRequest
from src.agents import orchestrator
from src.db.engine import AsyncSessionLocal
from src.db.repository import save_message, get_history, save_feedback
from src.logger import log


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sse_event(type_: str, content: str) -> str:
    return json.dumps({"type": type_, "content": content, "timestamp": _now()}, ensure_ascii=False)


async def handle_index(request: Request):
    import os
    index_path = os.path.join(os.path.dirname(__file__), "..", "web", "index.html")
    return FileResponse(os.path.abspath(index_path))


async def handle_chat_sse(request: Request):
    """SSE endpoint: стримит статусы и финальный ответ агента."""
    try:
        query = request.query_params.get("query", "").strip()
        session_id = request.query_params.get("session_id", "default")
        llm_provider = request.query_params.get("llm_provider", "gigachat")

        if not query:
            async def error_gen():
                yield {"data": _sse_event("error", "Запрос не может быть пустым")}
            return EventSourceResponse(error_gen())

        req = ChatRequest(query=query, session_id=session_id, llm_provider=llm_provider)
    except Exception as e:
        async def validation_error_gen():
            yield {"data": _sse_event("error", f"Неверный запрос: {str(e)}")}
        return EventSourceResponse(validation_error_gen())

    queue: asyncio.Queue = asyncio.Queue()

    async def status_callback(message: str):
        await queue.put(("status", message))

    async def agent_task():
        try:
            # Загружаем историю диалога
            async with AsyncSessionLocal() as db_session:
                chat_history = await get_history(req.session_id, db_session)

            final_answer = await orchestrator.run(
                query=req.query,
                session_id=req.session_id,
                llm_provider=req.llm_provider,
                chat_history=chat_history,
                status_callback=status_callback,
            )

            # Сохраняем в историю
            async with AsyncSessionLocal() as db_session:
                await save_message(req.session_id, "user", req.query, db_session)
                await save_message(req.session_id, "assistant", final_answer, db_session, "orchestrator")

            await queue.put(("result", final_answer))
        except Exception as e:
            log.error(f"[Handler] Ошибка агента: {e}")
            await queue.put(("error", f"Внутренняя ошибка: {str(e)}"))
        finally:
            await queue.put(("done", ""))

    async def event_generator():
        task = asyncio.create_task(agent_task())
        try:
            while True:
                try:
                    event_type, content = await asyncio.wait_for(queue.get(), timeout=120.0)
                except asyncio.TimeoutError:
                    yield {"data": _sse_event("error", "Превышено время ожидания ответа")}
                    break

                if event_type == "done":
                    yield {"data": _sse_event("done", "")}
                    break
                else:
                    yield {"data": _sse_event(event_type, content)}
        finally:
            task.cancel()

    return EventSourceResponse(event_generator())


async def handle_feedback(request: Request):
    try:
        body = await request.json()
        fb = FeedbackRequest(**body)
        async with AsyncSessionLocal() as db_session:
            await save_feedback(fb.session_id, fb.rating, fb.comment, db_session)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        log.error(f"[Handler] Ошибка сохранения обратной связи: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)


async def handle_health(request: Request):
    return JSONResponse({"status": "ok", "timestamp": _now()})
