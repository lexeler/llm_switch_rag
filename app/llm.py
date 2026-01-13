import os
from typing import List
import requests
from gigachat import GigaChat
from .kb import KBEntry

SYSTEM_PROMPT = """
Вы — профессиональный консультант по клиентским вопросам, знакомый с проектами нашей фирмы.
Отвечайте точно, понятно и по существу. Не отвечайте на вопросы, не связанные с деятельностью компании.
""".strip()


def _build_context(entries: List[KBEntry]) -> str:
    blocks = []
    for e in entries:
        text = f"{e.title}\n{e.body}".strip()
        if text:
            blocks.append(text)
    return "\n\n---\n\n".join(blocks)


def ask_yandex(question: str, entries: List[KBEntry]) -> str:
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")

    if not api_key or not folder_id:
        raise RuntimeError("Не заданы YANDEX_API_KEY и YANDEX_FOLDER_ID")

    kb_context = _build_context(entries)
    user_text = f"Вопрос клиента:\n{question}"
    if kb_context:
        user_text += f"\n\nОтветь на основе базы знаний:\n{kb_context}"

    resp = requests.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {api_key}",
            "x-folder-id": folder_id,
        },
        json={
            "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
            "completionOptions": {"stream": False, "temperature": 0.1, "maxTokens": 800},
            "messages": [
                {"role": "system", "text": SYSTEM_PROMPT},
                {"role": "user", "text": user_text},
            ],
        },
        timeout=60,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"YandexGPT: HTTP {resp.status_code}")

    return resp.json()["result"]["alternatives"][0]["message"]["text"]


def ask_gigachat(question: str, entries: List[KBEntry]) -> str:
    auth_data = os.getenv("GIGACHAT_AUTH_DATA")
    if not auth_data:
        raise RuntimeError("Не задана GIGACHAT_AUTH_DATA")

    kb_context = _build_context(entries)
    user_text = f"Вопрос клиента:\n{question}"
    if kb_context:
        user_text += f"\n\nОтветь на основе базы знаний:\n{kb_context}"

    prompt = f"{SYSTEM_PROMPT}\n\n---\n\n{user_text}"

    with GigaChat(
        credentials=auth_data,
        verify_ssl_certs=False,
        scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
    ) as giga:
        response = giga.chat(prompt)

    return response.choices[0].message.content or ""
