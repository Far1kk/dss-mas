import os
from dotenv import load_dotenv
from langchain_gigachat.chat_models import GigaChat
load_dotenv()

def get_gigachat_llm():
    return GigaChat(model="GigaChat-2", credentials=os.getenv("GIGACHAT_API_KEY"), verify_ssl_certs=False, scope="GIGACHAT_API_PERS")


if __name__ == "__main__":
    giga = get_gigachat_llm()
    print(giga.invoke("Hello, world!"))