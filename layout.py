import os
import subprocess
import shutil


def _run(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        return result.stdout.strip()
    except Exception:
        return ''


def is_wayland() -> bool:
    return bool(os.environ.get('WAYLAND_DISPLAY'))


def get_layout() -> str:
    """Return current keyboard layout as 'en' or 'ru'."""
    if shutil.which('xkb-switch'):
        raw = _run(['xkb-switch'])
    else:
        # Parse setxkbmap -query output
        raw = ''
        for line in _run(['setxkbmap', '-query']).splitlines():
            if line.startswith('layout:'):
                raw = line.split(':', 1)[1].strip().split(',')[0].strip()
                break

    raw = raw.lower()
    if raw.startswith('ru'):
        return 'ru'
    return 'en'


def switch_layout(target: str) -> None:
    """Switch keyboard layout to 'en' or 'ru'."""
    current = get_layout()
    if current == target:
        return

    # Try xkb-switch first
    if shutil.which('xkb-switch'):
        layout_name = 'ru' if target == 'ru' else 'us'
        _run(['xkb-switch', '-s', layout_name])
        return

    # Fallback: cycle through layouts using the switch shortcut via xdotool
    # This works when xkb-switch isn't available; assumes a single toggle hotkey.
    # A more reliable fallback is setxkbmap, but that resets layout state.
    if shutil.which('setxkbmap'):
        layout_name = 'ru' if target == 'ru' else 'us'
        _run(['setxkbmap', layout_name])
