"""Этап 4: строит 04_alias_phrases.json"""
import json
import random
import sys
from pathlib import Path

import pymorphy3
import razdel
import nltk

BASE = Path(__file__).parent
ALIAS_PATH = BASE / "01_indicator_alias.json"
SKELETON_PATH = BASE / "03_alias_phrases_skeleton.json"
SYNONYMS_PATH = BASE / "utils" / "synonyms.json"
STOPWORDS_PATH = BASE / "utils" / "stopwords_custom.txt"
OUT_PATH = BASE / "04_alias_phrases.json"

_morph = pymorphy3.MorphAnalyzer()

SIGNIFICANT_POS = {"NOUN", "ADJF", "ADJS", "PRTF", "PRTS"}

TEMPLATES: dict[str, list[str]] = {
    "head": [
        "что с {kw}",
        "как там {kw}",
        "много ли {kw}",
        "{kw} растёт",
        "состояние {kw}",
        "динамика {kw}",
        "ситуация по {kw}",
        "проблемы с {kw}",
        "что происходит с {kw}",
        "где у нас {kw}",
        "как дела с {kw}",
        "упал ли {kw}",
        "каков {kw}",
        "насколько {kw}",
        "тренд по {kw}",
    ],
    "news": [
        "{kw} в России",
        "темп роста {kw}",
        "{kw} по данным Росстата",
        "динамика {kw} за период",
        "изменение {kw} в годовом выражении",
        "показатель {kw} снизился",
        "показатель {kw} вырос",
        "объём {kw} в регионах",
        "статистика {kw}",
        "мониторинг {kw}",
        "анализ {kw}",
        "оценка {kw}",
        "{kw} по субъектам РФ",
        "рост {kw} за год",
        "снижение {kw} в регионе",
    ],
    "social": [
        "{kw} вообще норм?",
        "а как там {kw}?",
        "что по {kw}?",
        "{kw} опять просел",
        "кто видел {kw}?",
        "у нас ещё есть {kw}?",
        "{kw} вообще работает?",
        "интересно насчёт {kw}",
        "слышал про {kw}",
        "видел цифры по {kw}",
        "ну и как {kw}?",
        "{kw} совсем плохо",
        "что там с {kw}?",
        "расскажи про {kw}",
        "ктонибудь знает {kw}?",
    ],
    "synonyms": [
        "показатель {kw}",
        "индикатор {kw}",
        "метрика {kw}",
        "коэффициент {kw}",
        "измеритель {kw}",
        "уровень {kw}",
        "значение {kw}",
        "величина {kw}",
        "данные по {kw}",
        "цифры {kw}",
    ],
}


def get_stopwords() -> set[str]:
    try:
        ru_sw = set(nltk.corpus.stopwords.words("russian"))
    except LookupError:
        nltk.download("stopwords", quiet=True)
        ru_sw = set(nltk.corpus.stopwords.words("russian"))
    custom = set(STOPWORDS_PATH.read_text(encoding="utf-8").splitlines())
    return ru_sw | custom


def extract_keywords(name: str, stopwords: set[str]) -> list[str]:
    lemmas = []
    for tok in razdel.tokenize(name):
        t = tok.text.lower()
        parsed = _morph.parse(t)[0]
        lemma = parsed.normal_form
        pos = parsed.tag.POS
        if lemma not in stopwords and pos in SIGNIFICANT_POS and len(lemma) > 2:
            lemmas.append(lemma)
    return lemmas


def expand_with_synonyms(keywords: list[str], synonyms: dict[str, list[str]]) -> list[str]:
    expanded = list(keywords)
    for kw in keywords:
        expanded.extend(synonyms.get(kw, []))
    return list(dict.fromkeys(expanded))


def generate_phrases(keywords_expanded: list[str], templates: list[str], n: int) -> list[str]:
    candidates = []
    for kw in keywords_expanded:
        for tpl in templates:
            candidates.append(tpl.format(kw=kw))
    candidates = list(dict.fromkeys(candidates))
    random.shuffle(candidates)
    return candidates[:max(n, len(candidates))]


def build_phrases_entry(
    indicator: str,
    alias: str,
    indices: list[str],
    stopwords: set[str],
    synonyms: dict[str, list[str]],
) -> dict:
    keywords = extract_keywords(indicator, stopwords)
    if not keywords:
        keywords = [alias.lower()]
    keywords_exp = expand_with_synonyms(keywords, synonyms)

    phrases: dict[str, list[str]] = {}
    for source, templates in TEMPLATES.items():
        pool = generate_phrases(keywords_exp, templates, 5)
        phrases[source] = pool[:5] if len(pool) >= 5 else pool

    return {
        "alias": alias,
        "indices": indices,
        "phrases": phrases,
    }


def main():
    random.seed(42)
    skeleton = json.loads(SKELETON_PATH.read_text(encoding="utf-8"))
    synonyms = json.loads(SYNONYMS_PATH.read_text(encoding="utf-8"))
    stopwords = get_stopwords()

    result = {}
    for indicator, entry in skeleton.items():
        result[indicator] = build_phrases_entry(
            indicator,
            entry["alias"],
            entry["indices"],
            stopwords,
            synonyms,
        )

    total_phrases = sum(
        sum(len(v) for v in e["phrases"].values()) for e in result.values()
    )
    print(f"Показателей: {len(result)}, формулировок всего: {total_phrases}")

    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Записано → {OUT_PATH}")


if __name__ == "__main__":
    main()
