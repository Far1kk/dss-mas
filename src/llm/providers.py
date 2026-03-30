from enum import Enum


class LLMProvider(str, Enum):
    GIGACHAT = "gigachat"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"

    @classmethod
    def from_str(cls, value: str) -> "LLMProvider":
        value = value.lower().strip()
        for member in cls:
            if member.value == value:
                return member
        return cls.GIGACHAT  # fallback
