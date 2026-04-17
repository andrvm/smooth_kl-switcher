from corrector import EN_TO_RU, RU_TO_EN, convert_en_to_ru, convert_ru_to_en

# Cyrillic unicode block
_CYRILLIC = frozenset(chr(c) for c in range(0x0400, 0x0500))

# Common English words that should never be auto-corrected to Russian
COMMON_EN_WORDS: frozenset[str] = frozenset({
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'up', 'as', 'is', 'it', 'its', 'be', 'was',
    'are', 'were', 'been', 'has', 'have', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'can', 'shall', 'not', 'no',
    'yes', 'so', 'if', 'then', 'that', 'this', 'these', 'those', 'we', 'you',
    'he', 'she', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
    'his', 'our', 'their', 'all', 'any', 'some', 'more', 'most', 'other',
    'one', 'two', 'new', 'old', 'big', 'get', 'go', 'see', 'say', 'know',
    'use', 'make', 'come', 'take', 'good', 'day', 'now', 'way', 'out',
    'who', 'what', 'when', 'where', 'how', 'which', 'just', 'also', 'only',
    'into', 'over', 'back', 'time', 'well', 'even', 'want', 'give', 'work',
    'think', 'look', 'need', 'feel', 'try', 'leave', 'call', 'keep', 'let',
    'move', 'play', 'run', 'read', 'put', 'set', 'turn', 'show', 'open',
    'about', 'after', 'before', 'between', 'never', 'always', 'again',
    'here', 'there', 'still', 'first', 'last', 'next', 'right', 'left',
    'long', 'high', 'own', 'same', 'each', 'much', 'many', 'both', 'such',
    'real', 'true', 'like', 'very', 'too', 'down', 'off', 'then', 'than',
    'while', 'after', 'under', 'since', 'until', 'through', 'every', 'few',
    'name', 'home', 'hand', 'part', 'life', 'year', 'thing', 'world', 'help',
    'hold', 'find', 'live', 'ask', 'bring', 'start', 'tell', 'stop', 'cut',
    'add', 'buy', 'sell', 'send', 'meet', 'wait', 'plan', 'test', 'fix',
    'done', 'fine', 'sure', 'free', 'next', 'once', 'code', 'data', 'file',
    'line', 'list', 'page', 'site', 'user', 'type', 'mode', 'step', 'note',
    'text', 'form', 'menu', 'tool', 'view', 'link', 'sort', 'edit', 'save',
    'load', 'copy', 'move', 'size', 'date', 'rate', 'area', 'side', 'case',
    'able', 'full', 'main', 'near', 'past', 'fast', 'best', 'rest', 'lost',
    'hard', 'dark', 'wide', 'face', 'race', 'pain', 'rain', 'road', 'mind',
    'kind', 'find', 'sign', 'four', 'five', 'six', 'seven', 'eight', 'nine',
    'ten', 'zero', 'heat', 'seat', 'meet', 'feet', 'feel', 'reel', 'been',
    'seen', 'keen', 'tree', 'free', 'three', 'agree', 'care', 'dare', 'fare',
    'game', 'same', 'came', 'name', 'fame', 'late', 'gate', 'rate', 'fate',
    'note', 'vote', 'role', 'hole', 'sole', 'mole', 'cool', 'fool', 'pool',
    'tool', 'rule', 'blue', 'clue', 'true', 'glue', 'star', 'bar', 'car',
    'far', 'war', 'core', 'more', 'wore', 'bore', 'sure', 'pure', 'cure',
    'turn', 'burn', 'earn', 'learn', 'help', 'belt', 'melt', 'felt', 'sent',
    'went', 'rent', 'bent', 'lent', 'tent', 'dent', 'cent', 'vent', 'bold',
    'cold', 'fold', 'gold', 'hold', 'mold', 'sold', 'told', 'pink', 'link',
    'sink', 'rink', 'drink', 'think', 'thank', 'bank', 'rank', 'tank', 'lank',
    'mark', 'dark', 'park', 'lark', 'bark', 'harm', 'farm', 'warm', 'form',
    'port', 'sort', 'fort', 'cord', 'word', 'bird', 'firm', 'girl', 'bill',
    'fill', 'hill', 'kill', 'mill', 'pill', 'will', 'till', 'fell', 'bell',
    'cell', 'dell', 'hell', 'sell', 'tell', 'well', 'yell', 'ball', 'call',
    'fall', 'hall', 'tall', 'wall', 'pull', 'bull', 'full', 'dull', 'hull',
    'null', 'buzz', 'fuzz', 'jazz', 'fizz',
})


def script_of(text: str) -> str | None:
    """Return 'ru' if text is mostly Cyrillic, 'en' if mostly Latin, else None."""
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return None
    cyr = sum(1 for c in alpha if c in _CYRILLIC)
    lat = sum(1 for c in alpha if c.isascii())
    if cyr > lat:
        return 'ru'
    if lat > cyr:
        return 'en'
    return None


def _looks_wrong_layout_en(word: str) -> bool:
    """Heuristic: does this Latin word look like Russian typed in EN layout?"""
    lower = word.lower()

    if lower in COMMON_EN_WORDS:
        return False

    alpha = [c for c in lower if c.isalpha()]
    if not alpha:
        return False

    # High consonant ratio: Russian words in EN layout often have no vowels
    vowels = set('aeiou')
    vowel_count = sum(1 for c in alpha if c in vowels)
    consonant_ratio = 1.0 - vowel_count / len(alpha)
    if consonant_ratio >= 0.75 and len(alpha) >= 3:
        return True

    # Long consecutive consonant run (≥4 uncommon in English)
    max_run = cur_run = 0
    for c in lower:
        if c.isalpha() and c not in vowels:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 0
    if max_run >= 4:
        return True

    # Bigrams that are very common in RU-as-EN but rare in English
    unusual = {'jf', 'jd', 'jy', 'jn', 'jt', 'jh', 'jg', 'jk', 'jl',
               'uf', 'yf', 'hb', 'bk', 'xn', 'ij', 'gj', 'yt', 'yj',
               'nj', 'lf', 'vj', 'rf', 'rb', 'nb', 'ub', 'pb', 'kb',
               'dbr', 'ght', 'juj', 'jgj'}
    for pat in unusual:
        if pat in lower:
            return True

    return False


def _looks_valid_en(text: str) -> bool:
    """Return True if text plausibly looks like English (not gibberish)."""
    lower = text.lower()
    if lower in COMMON_EN_WORDS:
        return True
    alpha = [c for c in lower if c.isalpha()]
    if not alpha:
        return False
    vowels = set('aeiou')
    vowel_count = sum(1 for c in alpha if c in vowels)
    consonant_ratio = 1.0 - vowel_count / len(alpha)
    return consonant_ratio < 0.8


def check_word(word: str, current_layout: str) -> tuple[str, str] | None:
    """
    Analyze a typed word and return (target_layout, corrected_text) if a
    layout mismatch is detected, otherwise None.
    """
    if len(word) < 2:
        return None

    scr = script_of(word)

    if scr == 'en' and current_layout == 'en':
        # Latin typed in EN layout — check if it looks like wrong-layout Russian
        if _looks_wrong_layout_en(word):
            corrected = convert_en_to_ru(word)
            if script_of(corrected) == 'ru':
                return ('ru', corrected)

    elif scr == 'en' and current_layout == 'ru':
        # Latin typed but layout is now RU — classic glitch: switch didn't register
        corrected = convert_en_to_ru(word)
        if script_of(corrected) == 'ru':
            return ('ru', corrected)

    elif scr == 'ru' and current_layout == 'en':
        # Cyrillic typed but layout is now EN — user switched away after typing RU
        corrected = convert_ru_to_en(word)
        if _looks_valid_en(corrected):
            return ('en', corrected)

    return None
