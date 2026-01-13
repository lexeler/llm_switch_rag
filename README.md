# LLM Switch RAG

RAG-система с веб-интерфейсом для ответов на вопросы на основе базы знаний. Поддержка YandexGPT и GigaChat.

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

**Вручную:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 5002
```

**Как systemd сервис:**

1. Скопировать и настроить:
```bash
sudo cp llm_switch_rag.service /etc/systemd/system/
sudo nano /etc/systemd/system/llm_switch_rag.service
# Отредактировать пути и API ключи (YOUR_*)
```

2. Запустить:
```bash
sudo systemctl daemon-reload
sudo systemctl enable llm_switch_rag
sudo systemctl start llm_switch_rag
```

3. Управление:
```bash
sudo systemctl status llm_switch_rag  # Статус
sudo systemctl restart llm_switch_rag # Перезапуск
sudo systemctl stop llm_switch_rag    # Остановка
sudo journalctl -u llm_switch_rag -f  # Логи
```

4. Перезагрузка после изменения `.service` файла:
```bash
sudo systemctl daemon-reload
sudo systemctl restart llm_switch_rag
```

## Формат базы знаний

Текстовый файл с блоками, разделенными `##`:

```
##
Блок 1

##
Блок 2
```

## API

- `GET /` - веб-интерфейс
- `POST /upload_kb` - загрузка своей базы знаний (.txt)
- `POST /reset_kb` - сброс к стандартной базе
- `POST /ask` - отправка вопроса
