"""Этап 7: движок сопоставления запроса с облаками показателей.

Использование:
    cd semantic_dict
    python3 07_match_engine.py "сколько у нас исследователей в IT"
"""
import json
import sys
import time
from pathlib import Path

_BASE = Path(__file__).parent
sys.path.insert(0, str(_BASE / "utils"))
sys.path.insert(0, str(_BASE))

from preprocessing import preprocess, get_morph  # noqa: E402
from ngrams import build_ngrams  # noqa: E402

_CLOUDS_PATH = _BASE / "05_indicator_clouds.json"
_SYNONYMS_PATH = _BASE / "utils" / "synonyms.json"

_indicator_clouds: dict | None = None
_synonyms: dict | None = None
_indicator_vocab: set | None = None    # термины, присутствующие в ≥1 облаке
_rare_vocab: set | None = None         # термины с IDF-порогом (≤15% облаков)
_ruwordnet = None                      # None = не инициализирован; False = недоступен
_ruwn_cache: dict = {}                 # lemma → [synonyms], runtime-кеш


def _get_clouds() -> dict:
    global _indicator_clouds
    if _indicator_clouds is None:
        _indicator_clouds = json.loads(_CLOUDS_PATH.read_text(encoding="utf-8"))
    return _indicator_clouds


def _get_synonyms() -> dict:
    global _synonyms
    if _synonyms is None:
        _synonyms = json.loads(_SYNONYMS_PATH.read_text(encoding="utf-8"))
    return _synonyms


def _get_indicator_vocab() -> tuple[set, set]:
    """
    Возвращает два множества:
      vocab      — все термины, присутствующие хотя бы в 1 облаке показателя
      rare_vocab — термины, присутствующие не более чем в MAX_DF облаках
                   (IDF-фильтр: слишком частые слова — «деятельность», «дело» —
                   не являются дискриминаторами и исключаются из синонимного расширения)
    """
    global _indicator_vocab, _rare_vocab
    if _indicator_vocab is None:
        clouds = _get_clouds()
        total = len(clouds)
        MAX_DF = int(total * 0.15)   # ≤15% облаков → считаем специфичным
        freq: dict[str, int] = {}
        for data in clouds.values():
            for term in data["cloud"]:
                freq[term] = freq.get(term, 0) + 1
        _indicator_vocab = set(freq)
        _rare_vocab = {t for t, n in freq.items() if n <= MAX_DF}
    return _indicator_vocab, _rare_vocab


def _get_ruwordnet():
    global _ruwordnet
    if _ruwordnet is None:
        try:
            import ruwordnet
            _ruwordnet = ruwordnet.RuWordNet()
        except Exception:
            _ruwordnet = False
    return _ruwordnet if _ruwordnet else None


def _ruwordnet_synonyms(lemma: str) -> list[str]:
    """Live-поиск синонимов леммы в RuWordNet (с кешированием)."""
    if lemma in _ruwn_cache:
        return _ruwn_cache[lemma]
    wn = _get_ruwordnet()
    if not wn:
        _ruwn_cache[lemma] = []
        return []
    morph = get_morph()
    syns: set[str] = set()
    try:
        for synset in wn.get_synsets(lemma):
            for sense in synset.senses:
                s = morph.parse(sense.name.lower())[0].normal_form
                if s != lemma and len(s) > 2:
                    syns.add(s)
    except Exception:
        pass
    result = list(syns)
    _ruwn_cache[lemma] = result
    return result


def _expand_lemma(lemma: str, synonyms: dict, vocab: set, rare_vocab: set) -> list[str]:
    """
    Полный алгоритм расширения одной леммы запроса до контекстных синонимов.

    Шаг 1 — источник синонимов (приоритетность):
      a) synonyms.json  — ручные переопределения и RuWordNet от индикаторов
                          (если запись есть, она точнее и берётся как есть)
      b) RuWordNet live — для слов вне словаря показателей (любой запрос)

    Шаг 2 — фильтрация по словарю показателей:
      • термин должен присутствовать хотя бы в одном облаке показателя
        (иначе расширение никогда не даст совпадения)
      • термин не должен быть в >15% облаков (IDF-порог):
        слишком частые слова — «деятельность» (25%), «дело» (37%) —
        не различают показатели, а лишь раздувают пересечение
    """
    curated = synonyms.get(lemma)
    if curated is not None:
        # Curated запись: качество гарантировано, используем без IDF-фильтра.
        # Пустой список [] тоже считается curated — означает «не расширять».
        source = curated
        use_idf = False
    else:
        # Незнакомое слово: live-поиск в RuWordNet, применяем оба фильтра
        source = _ruwordnet_synonyms(lemma)
        use_idf = True

    result: list[str] = []
    for syn in source:
        for sg in build_ngrams(preprocess(syn), max_n=3):
            if sg not in vocab:
                continue                   # термина нет ни в одном показателе
            if use_idf and sg not in rare_vocab:
                continue                   # слишком частый — не дискриминатор
            if sg not in result:
                result.append(sg)

    return result


def build_query_cloud(query: str) -> dict[str, int]:
    """Строит облако лексем запроса: прямые термины + семантическое расширение."""
    lemmas = preprocess(query)
    cloud: dict[str, int] = {}

    # Прямые n-граммы из запроса — всегда включаются, без фильтров
    for g in build_ngrams(lemmas, max_n=3):
        cloud[g] = cloud.get(g, 0) + 1

    synonyms = _get_synonyms()
    vocab, rare_vocab = _get_indicator_vocab()

    for lemma in [g for g in cloud if "_" not in g]:
        for term in _expand_lemma(lemma, synonyms, vocab, rare_vocab):
            cloud[term] = cloud.get(term, 0) + 1

    return cloud


def match(query_cloud: dict[str, int], indicator_clouds: dict | None = None) -> list[dict]:
    """Сопоставляет облако запроса с облаками всех показателей.

    Возвращает список совпадений, отсортированный по убыванию Жаккара.
    """
    if indicator_clouds is None:
        indicator_clouds = _get_clouds()

    q_keys = set(query_cloud.keys())
    results = []

    for indicator, data in indicator_clouds.items():
        ind_cloud = data["cloud"]
        ind_keys = set(ind_cloud.keys())
        intersection = q_keys & ind_keys
        if not intersection:
            continue
        union = q_keys | ind_keys
        jaccard = len(intersection) / len(union)
        overlap = len(intersection) / min(len(q_keys), len(ind_keys))
        results.append(
            {
                "indicator": indicator,
                "alias": data["alias"],
                "indices": data["indices"],
                "matched_lexemes": sorted(intersection),
                "cloud_A_size": len(q_keys),
                "cloud_B_size": len(ind_keys),
                "intersection_size": len(intersection),
                "jaccard": round(jaccard, 4),
                "overlap": round(overlap, 4),
            }
        )

    return sorted(results, key=lambda x: x["jaccard"], reverse=True)


def search(query: str) -> list[dict]:
    """Полный пайплайн: строка запроса → отсортированный список результатов."""
    cloud = build_query_cloud(query)
    return match(cloud)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "сколько у нас исследователей в IT"
    t0 = time.time()
    results = search(query)
    elapsed = time.time() - t0

    print(f"Запрос: {query!r}")
    print(f"Совпадений: {len(results)}, время: {elapsed * 1000:.0f} мс")
    print()
    for r in results[:10]:
        print(
            f"  J={r['jaccard']:.4f}  O={r['overlap']:.4f}  [{r['alias']}]  "
            f"{r['indicator'][:65]}"
        )
        print(f"    совпало: {r['matched_lexemes'][:6]}")
