# core/llm_client.py
from openai import AsyncOpenAI
from .config import settings

async_client = AsyncOpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url=settings.DEEPSEEK_BASE_URL,
)