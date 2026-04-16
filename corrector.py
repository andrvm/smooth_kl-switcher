# Standard Russian QWERTY layout: physical key -> character produced
# Lowercase mappings per layout

_KEY_EN = {
    'KEY_Q': 'q', 'KEY_W': 'w', 'KEY_E': 'e', 'KEY_R': 'r', 'KEY_T': 't',
    'KEY_Y': 'y', 'KEY_U': 'u', 'KEY_I': 'i', 'KEY_O': 'o', 'KEY_P': 'p',
    'KEY_A': 'a', 'KEY_S': 's', 'KEY_D': 'd', 'KEY_F': 'f', 'KEY_G': 'g',
    'KEY_H': 'h', 'KEY_J': 'j', 'KEY_K': 'k', 'KEY_L': 'l',
    'KEY_Z': 'z', 'KEY_X': 'x', 'KEY_C': 'c', 'KEY_V': 'v', 'KEY_B': 'b',
    'KEY_N': 'n', 'KEY_M': 'm',
    'KEY_SEMICOLON': ';', 'KEY_APOSTROPHE': "'",
    'KEY_LEFTBRACE': '[', 'KEY_RIGHTBRACE': ']',
    'KEY_COMMA': ',', 'KEY_DOT': '.',
}

_KEY_RU = {
    'KEY_Q': 'й', 'KEY_W': 'ц', 'KEY_E': 'у', 'KEY_R': 'к', 'KEY_T': 'е',
    'KEY_Y': 'н', 'KEY_U': 'г', 'KEY_I': 'ш', 'KEY_O': 'щ', 'KEY_P': 'з',
    'KEY_A': 'ф', 'KEY_S': 'ы', 'KEY_D': 'в', 'KEY_F': 'а', 'KEY_G': 'п',
    'KEY_H': 'р', 'KEY_J': 'о', 'KEY_K': 'л', 'KEY_L': 'д',
    'KEY_Z': 'я', 'KEY_X': 'ч', 'KEY_C': 'с', 'KEY_V': 'м', 'KEY_B': 'и',
    'KEY_N': 'т', 'KEY_M': 'ь',
    'KEY_SEMICOLON': 'ж', 'KEY_APOSTROPHE': 'э',
    'KEY_LEFTBRACE': 'х', 'KEY_RIGHTBRACE': 'ъ',
    'KEY_COMMA': 'б', 'KEY_DOT': 'ю',
}

# Character-level conversion: what a Latin char maps to in Russian and vice versa
EN_TO_RU: dict[str, str] = {}
RU_TO_EN: dict[str, str] = {}

for _k in _KEY_EN:
    if _k in _KEY_RU:
        _en_lo, _ru_lo = _KEY_EN[_k], _KEY_RU[_k]
        EN_TO_RU[_en_lo] = _ru_lo
        EN_TO_RU[_en_lo.upper()] = _ru_lo.upper()
        RU_TO_EN[_ru_lo] = _en_lo
        RU_TO_EN[_ru_lo.upper()] = _en_lo.upper()


def convert_en_to_ru(text: str) -> str:
    return ''.join(EN_TO_RU.get(c, c) for c in text)


def convert_ru_to_en(text: str) -> str:
    return ''.join(RU_TO_EN.get(c, c) for c in text)
