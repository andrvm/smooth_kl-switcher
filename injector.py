import subprocess
import shutil
import time

from layout import switch_layout


def _xdotool(*args: str) -> None:
    subprocess.run(['xdotool', *args], capture_output=True)


def _ydotool(*args: str) -> None:
    subprocess.run(['ydotool', *args], capture_output=True)


def replace_text(delete_count: int, new_text: str, target_layout: str,
                 wayland: bool = False) -> None:
    """
    Delete `delete_count` characters then type `new_text` in `target_layout`.

    Sends BackSpace keystrokes to erase the wrongly-typed text, switches the
    keyboard layout, then types the corrected text.
    """
    switch_layout(target_layout)
    time.sleep(0.05)  # let the layout switch settle before typing

    if wayland:
        if shutil.which('ydotool'):
            for _ in range(delete_count):
                _ydotool('key', 'BackSpace')
            _ydotool('type', new_text)
    else:
        if shutil.which('xdotool'):
            _xdotool('key', '--clearmodifiers',
                     *(['BackSpace'] * delete_count))
            _xdotool('type', '--clearmodifiers', '--delay', '0', new_text)
