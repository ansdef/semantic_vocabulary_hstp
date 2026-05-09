"""Этап 6: пайплайн обработки пользовательского запроса.

Использование:
    cd semantic_dict
    python3 06_query_pipeline.py "запрос пользователя"

Или как модуль:
    import sys; sys.path.insert(0, 'semantic_dict')
    from semantic_dict.utils.preprocessing import preprocess
    ...  (см. 07_match_engine.py — там полный пайплайн)
"""
import json
import sys
from pathlib import Path

_BASE = Path(__file__).parent
sys.path.insert(0, str(_BASE / "utils"))

from preprocessing import preprocess  # noqa: E402
from ngrams import build_ngrams  # noqa: E402

_SYNONYMS: dict[str, list[str]] | None = None
_SYNONYMS_PATH = _BASE / "utils" / "synonyms.json"


def _get_synonyms() -> dict[str, list[str]]:
    global _SYNONYMS
    if _SYNONYMS is None:
        _SYNONYMS = json.loads(_SYNONYMS_PATH.read_text(encoding="utf-8"))
    return _SYNONYMS


def build_query_cloud(query: str) -> dict[str, int]:
    """Принимает строку запроса, возвращает {лексема: количество_вхождений}."""
    lemmas = preprocess(query)
    cloud: dict[str, int] = {}

    grams = build_ngrams(lemmas, max_n=3)
    for g in grams:
        cloud[g] = cloud.get(g, 0) + 1

    synonyms = _get_synonyms()
    for lemma in [g for g in grams if "_" not in g]:
        for syn in synonyms.get(lemma, [])[:3]:
            syn_lemmas = preprocess(syn)
            if not syn_lemmas:
                continue
            for sg in build_ngrams(syn_lemmas, max_n=3):
                cloud[sg] = cloud.get(sg, 0) + 1

    return cloud


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "сколько у нас исследователей в IT"
    cloud = build_query_cloud(query)
    print(f"Запрос: {query!r}")
    print(f"Облако ({len(cloud)} лексем):")
    for lex, w in sorted(cloud.items(), key=lambda x: -x[1]):
        print(f"  {w} {lex}")
