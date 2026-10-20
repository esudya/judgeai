import httpx

from src.config import settings


async def generate_answer(prompt: str) -> str:
    if not settings.LLM_API_KEY:
        return "LLM не настроен. Задайте LLM_API_KEY в .env."

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.1,
    }

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{settings.LLM_API_BASE}/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]
