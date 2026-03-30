from sqlalchemy.ext.asyncio import AsyncSession
from src.db.repository import save_message, get_history


class ConversationMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id

    async def add_message(
        self,
        role: str,
        content: str,
        db_session: AsyncSession,
        agent_type: str | None = None,
    ) -> None:
        await save_message(
            session_id=self.session_id,
            role=role,
            content=content,
            db_session=db_session,
            agent_type=agent_type,
        )

    async def get_formatted_history(
        self, db_session: AsyncSession, limit: int = 10
    ) -> list[dict]:
        return await get_history(
            session_id=self.session_id,
            db_session=db_session,
            limit=limit,
        )
