# Семантический словарь для ИИ-платформы НТР

Словарь обеспечивает семантический поиск по ~1200 статистическим показателям
регионального развития на основе облаков лексем и метрики Жаккара.

## Структура артефактов

```
semantic_dict/
  01_indicator_alias.json      — показатель → alias (аббревиатура)
  02_indicator_index.json      — показатель → индексы (economic/personnel/innovation/resource)
  02_unclassified.log          — показатели без индекса
  03_alias_phrases_skeleton.json — скелет: alias + indices + пустые phrases
  04_alias_phrases.json        — alias + indices + сгенерированные формулировки
  05_indicator_clouds.json     — облака лексем (uni/bi/триграммы) с весами
  06_query_pipeline.py         — обработка пользовательского запроса → облако
  07_match_engine.py           — матчинг облака запроса с облаками показателей
  08_deploy_beget.md           — инструкция по развёртыванию на Beget Noble
  data/
    indicators.parquet         — исходные данные
  utils/
    preprocessing.py           — лемматизация, токенизация, стоп-слова
    ngrams.py                  — генерация n-грамм и облаков
    stopwords_custom.txt       — кастомный стоп-лист
    keywords_indices.json      — корни ключевых слов для классификации по индексам
    synonyms.json              — синонимы лемм для расширения запросов
```

## Быстрый старт

### Установка

```bash
pip install pandas pyarrow pymorphy3 razdel nltk
python3 -c "import nltk; nltk.download('stopwords')"
```

### Пересборка всех артефактов

```bash
cd semantic_dict
python3 00_build_synonyms.py
python3 01_build_alias.py     data/indicators.parquet
python3 02_build_index.py
python3 03_build_skeleton.py
python3 04_generate_phrases.py
python3 05_build_clouds.py
```

### Тестовый запрос

```bash
cd semantic_dict
python3 07_match_engine.py "сколько у нас исследователей в IT"
```

Пример вывода:

```
Запрос: 'сколько у нас исследователей в IT'
Совпадений: 118, время: 44 мс

  J=0.0946  O=0.7778  [ЧИУСУСДН]  Численность исследователей с учеными степенями...
    совпало: ['исследователь', 'научный', 'научный_работник', 'работник', 'сотрудник', 'учёный']
```

## Четыре индекса

| Код | Название |
|-----|----------|
| `economic` | Экономический |
| `personnel` | Кадровый |
| `innovation` | Инновационный |
| `resource` | Ресурсный |

## Метрики ранжирования

- **Жаккар** `J = |A ∩ B| / |A ∪ B|` — основная, ранжирующая
- **Overlap** `|A ∩ B| / min(|A|, |B|)` — устойчив к разнице размеров облаков

Финальная сортировка — по убыванию Жаккара.

## Развёртывание

См. `08_deploy_beget.md`.
