# Развёртывание на Beget Noble

## Архитектура

Backend на Python (FastAPI), эндпоинт `POST /match` с телом `{"query": "..."}`.
Облака показателей подгружаются один раз при старте процесса (~5–20 МБ для 1200 показателей).

## Структура на сервере

```
~/sites/<домен>/
  app/
    main.py
    match_engine.py        ← копия semantic_dict/07_match_engine.py
    query_pipeline.py      ← копия semantic_dict/06_query_pipeline.py
    utils/
      preprocessing.py
      ngrams.py
      stopwords_custom.txt
      synonyms.json
    data/
      indicator_clouds.json
  venv/
  requirements.txt
```

## Пример main.py

```python
from fastapi import FastAPI
from pydantic import BaseModel
import json
from pathlib import Path

# путь к данным относительно main.py
from match_engine import search

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/match")
def match_endpoint(req: QueryRequest):
    results = search(req.query)
    return {"query": req.query, "count": len(results), "results": results[:50]}
```

## Пошаговая инструкция

### 1. SSH-доступ

В панели Beget: раздел **SSH** → создать пароль или SSH-ключ.

```bash
ssh login@login.beget.tech
```

### 2. Python-окружение

На Beget Noble доступен Python 3.10+:

```bash
cd ~/sites/<домен>/
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install fastapi "uvicorn[standard]" pymorphy3 razdel pyarrow pandas nltk
pip freeze > requirements.txt
```

После установки скачать данные NLTK:

```bash
python3 -c "import nltk; nltk.download('stopwords')"
```

### 3. Загрузка артефактов

Через SFTP (FileZilla, WinSCP) или `scp`:

```bash
scp -r semantic_dict/utils       login@login.beget.tech:~/sites/<домен>/app/utils/
scp semantic_dict/05_indicator_clouds.json \
    login@login.beget.tech:~/sites/<домен>/app/data/indicator_clouds.json
scp semantic_dict/07_match_engine.py  login@login.beget.tech:~/sites/<домен>/app/match_engine.py
scp semantic_dict/06_query_pipeline.py login@login.beget.tech:~/sites/<домен>/app/query_pipeline.py
# main.py — создать вручную по шаблону выше
```

### 4. Запуск как постоянного процесса

В панели Beget: **Сайты** → **Управление** → вкладка **Python**:

- **Точка входа:** `app.main:app`
- **Порт:** выделяемый Beget'ом (переменная `$PORT`)
- **Команда запуска:**
  ```
  uvicorn app.main:app --host 127.0.0.1 --port $PORT --workers 2
  ```

### 5. Проксирование через nginx

В панели для домена включить **Проксирование** на тот же порт.
Внешний URL: `https://<домен>/match`.

### 6. Тестирование

```bash
curl -X POST https://<домен>/match \
     -H "Content-Type: application/json" \
     -d '{"query": "сколько у нас исследователей в IT"}'
```

Ожидаемый ответ (< 500 мс):

```json
{
  "query": "сколько у нас исследователей в IT",
  "count": 118,
  "results": [
    {
      "indicator": "Численность исследователей с учеными степенями: С ученой степенью...",
      "alias": "ЧИУСУСДН",
      "indices": ["personnel"],
      "matched_lexemes": ["исследователь", "научный", "работник", ...],
      "jaccard": 0.0946,
      "overlap": 0.7778
    },
    ...
  ]
}
```

### 7. Логи

В панели Beget: **Логи приложений** → или напрямую в `~/sites/<домен>/logs/`.

### 8. Обновление данных

1. Запустить пайплайн локально заново (после обновления parquet-файла):
   ```bash
   python3 semantic_dict/01_build_alias.py data/indicators.parquet
   python3 semantic_dict/02_build_index.py
   python3 semantic_dict/03_build_skeleton.py
   python3 semantic_dict/04_generate_phrases.py
   python3 semantic_dict/05_build_clouds.py
   ```
2. Загрузить новый `05_indicator_clouds.json` через SFTP.
3. Нажать **Перезапустить** в панели Python.

## Альтернатива без backend

Все JSON в `~/sites/<домен>/public_html/data/`, препроцессинг и матчинг на клиентском JS.
Уместно при облаках до ~5 МБ и отсутствии требований к скрытию данных.

## Требования к ресурсам

| Параметр | Значение |
|----------|----------|
| RAM (облака в памяти) | ~30–80 МБ |
| CPU на запрос | < 50 мс |
| Хранилище (JSON) | ~20–40 МБ |
| Python | 3.10+ |
| Тариф | Beget Noble (подходит) |
