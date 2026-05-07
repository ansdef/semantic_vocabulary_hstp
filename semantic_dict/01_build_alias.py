"""Этап 1: строит 01_indicator_alias.json"""
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pymorphy3
import razdel

PARQUET_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/indicators.parquet"
OUT_PATH = Path(__file__).parent / "01_indicator_alias.json"

KNOWN = {
    "ввп": "ВВП",
    "врп": "ВРП",
    "ниокр": "НИОКР",
    "мсп": "МСП",
    "икт": "ИКТ",
}

SERVICE_POS = {"PREP", "CONJ", "PRCL", "INTJ"}
SIGNIFICANT_POS = {"NOUN", "ADJF", "ADJS", "PRTF", "PRTS", "NUMR", "NPRO"}

_morph = pymorphy3.MorphAnalyzer()


def significant_tokens(name: str) -> list[str]:
    tokens = []
    for tok in razdel.tokenize(name):
        t = tok.text
        p = _morph.parse(t)[0]
        pos = p.tag.POS
        if pos not in SERVICE_POS and len(t) > 1:
            tokens.append(t)
    return tokens


def make_abbr(tokens: list[str]) -> str:
    letters = []
    for t in tokens:
        m = re.match(r"[А-ЯЁа-яёA-Za-z]", t)
        if m:
            letters.append(m.group().upper())
    return "".join(letters)


def build_alias(name: str) -> str:
    name_lower = name.lower()

    for kw, alias in KNOWN.items():
        if kw in name_lower:
            return alias

    if re.search(r"\bit\b", name, re.IGNORECASE):
        return "IT-кадры"

    sig = significant_tokens(name)
    if not sig:
        return name[:10].replace(" ", "_")

    abbr = make_abbr(sig)

    if len(abbr) < 2:
        abbr = sig[0][:10]

    bad = re.search(r"[БВГДЖЗКЛМНПРСТФХЦЧШЩ]{4,}", abbr)
    if bad or len(abbr) > 20:
        abbr = "".join(t[0].upper() for t in sig[:4])

    abbr = abbr[:20]
    return abbr if len(abbr) >= 2 else sig[0][:10]


def main():
    df = pd.read_parquet(PARQUET_PATH)
    names = sorted(
        {n for n in df["indicator_name"].dropna() if isinstance(n, str) and n.strip()}
    )
    print(f"Показателей: {len(names)}")

    result = {}
    for name in names:
        result[name] = build_alias(name)

    assert all(k and v for k, v in result.items()), "Есть пустые ключи/значения"

    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Записано: {OUT_PATH}")


if __name__ == "__main__":
    main()
