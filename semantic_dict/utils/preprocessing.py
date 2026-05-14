import re
import pymorphy3
import razdel
import nltk
from pathlib import Path

_morph = None
_stopwords = None

CUSTOM_STOPWORDS_PATH = Path(__file__).parent / "stopwords_custom.txt"


def get_morph():
    global _morph
    if _morph is None:
        _morph = pymorphy3.MorphAnalyzer()
    return _morph


def get_stopwords():
    global _stopwords
    if _stopwords is None:
        try:
            ru_sw = set(nltk.corpus.stopwords.words("russian"))
        except LookupError:
            nltk.download("stopwords", quiet=True)
            ru_sw = set(nltk.corpus.stopwords.words("russian"))
        custom = set()
        if CUSTOM_STOPWORDS_PATH.exists():
            custom = set(CUSTOM_STOPWORDS_PATH.read_text(encoding="utf-8").splitlines())
        _stopwords = ru_sw | custom
    return _stopwords


# Аббревиатуры и термины, которые regex или морфология разрушают — нормализуем заранее.
# Ключи — regex-паттерны, значения — замена перед лемматизацией.
_ABBREV = {
    # Латинские аббревиатуры (regex их разрушает через &, или оставляет 1-буквенные токены)
    r"\br\s*&\s*d\b":        "исследование разработка",
    r"\bр\s*&\s*д\b":        "исследование разработка",
    r"\broi\b":               "рентабельность норма",
    r"\bkpi\b":               "коэффициент индекс",
    r"\bhr\b":                "кадр персонал численность",
    r"\besg\b":               "экология социальный управление",
    r"\bai\b":                "информационный технология цифровой",
    # IT: и латиница 'it', и кириллица 'ит'
    r"\bit\b":                "информационный технология",
    r"\bит\b":                "информационный технология",
    r"\bиии\b":               "информационный технология цифровой",   # ИИИ (ИИ)
    r"\bикт\b":               "информационный коммуникационный технология",
    # Российские аббревиатуры
    r"\bниокр\b":             "исследование разработка инновация",
    r"\bкпд\b":               "эффективность производительность",
    r"\bжкх\b":               "жилищный коммунальный",
    r"\bмсп\b":               "малый предприниматель бизнес",
    r"\bврп\b":               "валовый региональный продукт",
    r"\bввп\b":               "валовый внутренний продукт",
    r"\bврн\b":               "валовый региональный",
    r"\bфот\b":               "фонд оплата труд",
    r"\bпфр\b":               "пенсия фонд",
    r"\bомс\b":               "медицинский страхование",
    r"\bндс\b":               "налог добавленный стоимость",
    r"\bндфл\b":              "налог доход физический лицо",
    r"\bзп\b":                "заработный плата",
    r"\bмрот\b":              "заработный плата минимальный",
    r"\bпмж\b":               "жильё постоянный место жительство",
    # Регионы — только конкретные топонимы, без generic «регион/округ»
    r"\bмо\b":                "московский область",
    r"\bспб\b":               "санкт петербург",
    r"\bмск\b":               "москва",
    r"\bдфо\b":               "дальний восток",
    r"\bсфо\b":               "сибирь",
    r"\bцфо\b":               "центральный федеральный",
}


def _normalize(text: str) -> str:
    for pat, repl in _ABBREV.items():
        text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    return text


def preprocess(text: str) -> list[str]:
    morph = get_morph()
    stopwords = get_stopwords()

    text = text.lower()
    text = _normalize(text)
    text = re.sub(r"[^\w\s\-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"(?<!\w)-|-(?!\w)", " ", text)

    tokens = [t.text for t in razdel.tokenize(text)]
    lemmas = []
    for token in tokens:
        if not token.strip():
            continue
        lemma = morph.parse(token)[0].normal_form
        if lemma in stopwords:
            continue
        if len(lemma) <= 1:
            continue
        if re.fullmatch(r"\d+", lemma):
            continue
        lemmas.append(lemma)

    return lemmas
