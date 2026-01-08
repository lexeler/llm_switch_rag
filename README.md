# LLM Switch RAG

RAG-система с переключением между YandexGPT и GigaChat.

## Запуск

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 5002
```

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `YANDEX_API_KEY` | API-ключ Yandex Cloud |
| `YANDEX_FOLDER_ID` | ID каталога Yandex Cloud |
| `GIGACHAT_AUTH_DATA` | Authorization Key GigaChat |
| `GIGACHAT_SCOPE` | `GIGACHAT_API_PERS` (по умолчанию) |

## Структура

```
├── app/
│   ├── kb.py      # поиск по базе знаний
│   ├── llm.py     # YandexGPT и GigaChat
│   └── main.py    # FastAPI + веб-интерфейс
├── knowledge_base.txt   # база знаний (разделитель ##)
└── requirements.txt
```

## Systemd-сервис

Токены и настройки: `/etc/systemd/system/llm_switch_rag.service`

```bash
sudo systemctl restart llm_switch_rag    # перезапуск
sudo systemctl status llm_switch_rag     # статус
sudo journalctl -u llm_switch_rag -n 50  # логи
```

После изменения токенов:
```bash
sudo systemctl daemon-reload
sudo systemctl restart llm_switch_rag
```

## База знаний

Формат `knowledge_base.txt` — блоки разделены `##`:

```
##
Заголовок блока
Текст блока
#тег1 #тег2

##
Другой блок
Другой текст
```
