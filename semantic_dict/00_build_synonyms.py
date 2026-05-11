"""Этап 0: строит utils/synonyms.json.

Загружает все названия показателей из parquet, извлекает леммы,
ищет синонимы в RuWordNet для каждой из них, дополняет встроенным словарём.
"""
import json
import sys
from pathlib import Path

import pymorphy3
import razdel
import pandas as pd

BASE = Path(__file__).parent
STOPWORDS_PATH = BASE / "utils" / "stopwords_custom.txt"
OUT_PATH = BASE / "utils" / "synonyms.json"
PARQUET_PATH = BASE / "data" / "indicators.parquet"

_morph = pymorphy3.MorphAnalyzer()

# Дополнительный словарь для терминов, которые RuWordNet не покрывает
EXTRA: dict[str, list[str]] = {
    # разговорные / сленговые формы
    "деньги":       ["финансы", "доход", "средство", "денежный"],
    "денежный":     ["деньги", "финансовый", "финансы"],
    "финансовый":   ["денежный", "деньги", "финансы"],
    "финансы":      ["деньги", "бюджет", "денежный"],
    "молочка":      ["молоко", "молочный", "надой"],
    "айтишник":     ["ит", "информационный", "программист", "разработчик", "специалист"],
    "айтишников":   ["ит", "информационный", "программист"],
    "говядина":     ["мясо", "скот", "животноводство", "крупный"],
    "мясо":         ["говядина", "животноводство", "скот"],
    "зерно":        ["зерновые", "пшеница", "урожай", "злак", "посев"],
    "зерновые":     ["зерно", "пшеница", "урожай", "злак"],
    "урожай":       ["зерно", "зерновые", "сбор", "растениеводство"],
    "молочка":      ["молоко", "молочный", "надой"],
    "работа":       ["безработица", "занятость", "труд"],
    "человек":      ["численность", "население", "число"],
    "дом":          ["жильё", "жилой", "здание", "квартира"],
    "жкх":          ["жилищный", "коммунальный", "услуга"],
    "вуз":          ["университет", "институт", "студент"],
    "ит":           ["цифровой", "информационный", "технология", "айти"],
    "айти":         ["ит", "цифровой", "информационный"],
    "ниокр":        ["инновация", "разработка", "исследование"],
    "r&d":          ["ниокр", "исследование", "разработка", "инновация"],
    "roi":          ["рентабельность", "доходность", "прибыльность"],
    "мсп":          ["малый", "предприниматель", "бизнес"],
    "врп":          ["валовый", "региональный", "продукт", "ввп"],
    "ввп":          ["валовый", "продукт", "врп"],
    "отток":        ["миграция", "убыль", "снижение", "уменьшение"],
    "сбор":         ["урожай", "производство", "заготовка"],
    "молоко":       ["молочный", "молочка", "надой"],
    "молочный":     ["молоко", "молочка"],
    "скот":         ["животноводство", "корова", "поголовье"],
    "животноводство": ["скот", "корова", "поголовье"],
    "фермерский":   ["сельскохозяйственный", "аграрный", "крестьянский"],
    "рыба":         ["рыболовство", "рыбоводство", "аквакультура"],
}


def get_indicator_names() -> list[str]:
    df = pd.read_parquet(PARQUET_PATH)
    return df["indicator_name"].dropna().unique().tolist()


def extract_lemmas(names: list[str], stopwords: set) -> list[str]:
    """Все уникальные значимые леммы из названий показателей."""
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        for tok in razdel.tokenize(name):
            t = tok.text.lower()
            if not t.strip() or len(t) < 3:
                continue
            lemma = _morph.parse(t)[0].normal_form
            if lemma in stopwords or len(lemma) < 3 or lemma in seen:
                continue
            seen.add(lemma)
            result.append(lemma)
    return result


def build_ruwordnet_synonyms(lemmas: list[str]) -> dict[str, list[str]]:
    import ruwordnet
    wn = ruwordnet.RuWordNet()
    result: dict[str, list[str]] = {}
    for lemma in lemmas:
        synonyms: set[str] = set()
        for synset in wn.get_synsets(lemma):
            for sense in synset.senses:
                syn_lemma = _morph.parse(sense.name.lower())[0].normal_form
                if syn_lemma != lemma and len(syn_lemma) > 2:
                    synonyms.add(syn_lemma)
        if synonyms:
            result[lemma] = list(synonyms)[:6]
    return result


def main():
    stopwords = set(STOPWORDS_PATH.read_text(encoding="utf-8").splitlines())

    print("Загружаем показатели из parquet…")
    names = get_indicator_names()
    print(f"  показателей: {len(names)}")

    lemmas = extract_lemmas(names, stopwords)
    print(f"  уникальных лемм: {len(lemmas)}")

    print("Ищем синонимы в RuWordNet…")
    ruwn = build_ruwordnet_synonyms(lemmas)
    print(f"  лемм с синонимами из RuWordNet: {len(ruwn)}")

    # Сливаем: EXTRA дополняет RuWordNet там, где он не покрывает
    merged: dict[str, list[str]] = {}
    for lemma in set(ruwn) | set(EXTRA):
        combined = []
        seen: set[str] = set()
        for syn in (ruwn.get(lemma, []) + EXTRA.get(lemma, [])):
            if syn != lemma and syn not in seen:
                seen.add(syn)
                combined.append(syn)
        if combined:
            merged[lemma] = combined[:8]

    OUT_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Записано: {len(merged)} лемм → {OUT_PATH}")


if __name__ == "__main__":
    main()
