import logging
import sys

logger = logging.getLogger(__name__)


LOG_FILE = 'app.log'


class Logger:
    def __init__(self, log_file):
        # Настройка логгера
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),  # Запись в файл
                logging.StreamHandler(sys.stdout)  # Вывод в консоль
            ]
        )

    @staticmethod
    def message(message):
        # Запись сообщения в лог
        logger.info(message)

if __name__ == "__main__":
    # Настройка логгера
    log = Logger(LOG_FILE)
    log.message('hello world')
