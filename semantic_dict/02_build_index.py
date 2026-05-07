"""Этап 2: строит 02_indicator_index.json и 02_unclassified.log"""
import json
import sys
from pathlib import Path

import pymorphy3
import razdel

BASE = Path(__file__).parent
ALIAS_PATH = BASE / "01_indicator_alias.json"
KEYWORDS_PATH = BASE / "utils" / "keywords_indices.json"
OUT_PATH = BASE / "02_indicator_index.json"
UNCLASSIFIED_LOG = BASE / "02_unclassified.log"

_morph = pymorphy3.MorphAnalyzer()

INDEX_DESCRIPTIONS = {
    "economic": """
        валовой внутренний продукт валовой региональный продукт добавленная стоимость
        доход выручка прибыль рентабельность экспорт импорт торговля оборот цена тариф
        инфляция дефлятор продажи реализация налог бюджет субсидия дотация трансферт
        инвестиция стоимость себестоимость финансовый результат денежный поток капитальное вложение
    """,
    "personnel": """
        кадры персонал сотрудник занятость безработица исследователь учёный аспирант докторант
        выпускник студент образование обучение переподготовка квалификация компетенция
        оплата труда заработная плата производительность труда трудовой ресурс рабочая сила
        численность работник специалист миграция текучесть
    """,
    "innovation": """
        инновация патент лицензия ниокр разработка изобретение полезная модель промышленный образец
        публикация цитируемость цифровизация автоматизация стартап технопарк
        интеллектуальная собственность ноу-хау передовая технология критическая технология
    """,
    "resource": """
        основной фонд основное средство амортизация капитал фондоотдача фондовооружённость
        фондоёмкость производственная мощность загрузка инфраструктура финансирование
        сырьё материал запас энергия энергоресурс энергоёмкость энергоэффективность
        ресурсоотдача материалоёмкость топливо электроэнергия теплоэнергия водоснабжение
    """,
}


def lemmatize_name(name: str) -> set[str]:
    lemmas = set()
    for tok in razdel.tokenize(name.lower()):
        t = tok.text
        if len(t) > 1:
            lemmas.add(_morph.parse(t)[0].normal_form)
    return lemmas


def classify_by_keywords(lemmas: set[str], keywords: dict[str, list[str]]) -> list[str]:
    matched = []
    for index_code, roots in keywords.items():
        for lemma in lemmas:
            for root in roots:
                if lemma.startswith(root):
                    matched.append(index_code)
                    break
            else:
                continue
            break
    return list(dict.fromkeys(matched))


def fallback_classify(indicator_lemmas: set[str], index_descriptions: dict) -> list[str]:
    results = []
    for index_code, description in index_descriptions.items():
        desc_lemmas = {
            _morph.parse(token)[0].normal_form
            for token in description.split()
            if len(token) > 1
        }
        intersection = indicator_lemmas & desc_lemmas
        if intersection:
            results.append(index_code)
    return results


def main():
    alias_data = json.loads(ALIAS_PATH.read_text(encoding="utf-8"))
    keywords = json.loads(KEYWORDS_PATH.read_text(encoding="utf-8"))

    records = []
    unclassified = []

    for indicator, alias in alias_data.items():
        lemmas = lemmatize_name(indicator)
        indices = classify_by_keywords(lemmas, keywords)

        if not indices:
            indices = fallback_classify(lemmas, INDEX_DESCRIPTIONS)

        if not indices:
            unclassified.append(indicator)
        else:
            for idx in indices:
                records.append({"indicator": indicator, "alias": alias, "index": idx})

    OUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    UNCLASSIFIED_LOG.write_text("\n".join(unclassified), encoding="utf-8")

    print(f"Записей в индексе: {len(records)}")
    print(f"Неклассифицировано: {len(unclassified)}")
    if unclassified[:5]:
        for u in unclassified[:5]:
            print(" -", u)


if __name__ == "__main__":
    main()
