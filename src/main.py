import sys
import os

# Добавляем корень проекта в путь чтобы `src.*` находился при запуске python src/main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from dotenv import load_dotenv

load_dotenv()

from src.api.app import create_app
from src.config import settings
from src.logger import log


def main():
    log.info(f"Запуск сервера на {settings.app_host}:{settings.app_port}")
    app = create_app()
    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
