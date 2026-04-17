import os
import re
import time
import subprocess

# ── layout cache (100 ms TTL) to avoid subprocess per keystroke ──────────────
_cache_value: str = 'en'
_cache_time: float = 0.0
_CACHE_TTL = 0.1


def get_layout_cached() -> str:
    global _cache_value, _cache_time
    now = time.monotonic()
    if now - _cache_time > _CACHE_TTL:
        _cache_value = get_layout()
        _cache_time = now
    return _cache_value


# ── helpers ───────────────────────────────────────────────────────────────────

def _run(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        return result.stdout.strip()
    except Exception:
        return ''


def is_wayland() -> bool:
    return bool(os.environ.get('WAYLAND_DISPLAY'))


def _is_gnome() -> bool:
    return 'GNOME' in os.environ.get('XDG_CURRENT_DESKTOP', '').upper()


# ── GNOME Wayland: layout via gsettings ──────────────────────────────────────

def _gnome_sources() -> list[str]:
    """Return list of layout names from gsettings, e.g. ['us', 'ru']."""
    raw = _run(['gsettings', 'get', 'org.gnome.desktop.input-sources', 'sources'])
    # raw looks like: [('xkb', 'us'), ('xkb', 'ru')]
    return re.findall(r"'xkb',\s*'([^']+)'", raw)


def _gnome_current_index() -> int:
    raw = _run(['gsettings', 'get', 'org.gnome.desktop.input-sources', 'current'])
    # raw looks like: uint32 0
    m = re.search(r'\d+', raw)
    return int(m.group()) if m else 0


def _get_layout_gnome() -> str:
    sources = _gnome_sources()
    if not sources:
        return 'en'
    idx = _gnome_current_index()
    active = sources[idx] if idx < len(sources) else sources[0]
    return 'ru' if active.startswith('ru') else 'en'


def _switch_layout_gnome(target: str) -> None:
    sources = _gnome_sources()
    target_prefix = 'ru' if target == 'ru' else 'us'
    for i, src in enumerate(sources):
        if src.startswith(target_prefix) or (target == 'en' and not src.startswith('ru')):
            _run(['gsettings', 'set', 'org.gnome.desktop.input-sources',
                  'current', str(i)])
            return


# ── X11: layout via setxkbmap ─────────────────────────────────────────────────

def _get_layout_x11() -> str:
    for line in _run(['setxkbmap', '-query']).splitlines():
        if line.startswith('layout:'):
            raw = line.split(':', 1)[1].strip().split(',')[0].strip().lower()
            return 'ru' if raw.startswith('ru') else 'en'
    return 'en'


def _switch_layout_x11(target: str) -> None:
    _run(['setxkbmap', 'ru' if target == 'ru' else 'us'])


# ── public API ────────────────────────────────────────────────────────────────

def get_layout() -> str:
    """Return current keyboard layout as 'en' or 'ru'."""
    if is_wayland() and _is_gnome():
        return _get_layout_gnome()
    return _get_layout_x11()


def switch_layout(target: str) -> None:
    """Switch keyboard layout to 'en' or 'ru'."""
    if get_layout() == target:
        return
    if is_wayland() and _is_gnome():
        _switch_layout_gnome(target)
    else:
        _switch_layout_x11(target)
