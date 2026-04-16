import threading
from typing import Callable

from pynput import keyboard as kb

# Keys that end a word and trigger analysis
_BOUNDARY_CHARS = {' ', '\t', '\r', '\n'}

# Keys that represent non-char word terminators
_BOUNDARY_SPECIAL = {
    kb.Key.space, kb.Key.enter, kb.Key.tab,
}


class KeyboardListener:
    """
    Listens to keyboard events and exposes three callbacks:
      on_char(char)          — a printable character was typed
      on_boundary(char)      — a word-boundary key was pressed (space/enter/tab)
      on_backspace()         — backspace was pressed
    """

    def __init__(
        self,
        on_char: Callable[[str], None],
        on_boundary: Callable[[str], None],
        on_backspace: Callable[[], None],
    ) -> None:
        self._on_char = on_char
        self._on_boundary = on_boundary
        self._on_backspace = on_backspace
        self._listener: kb.Listener | None = None
        self._suppress_until = threading.Event()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ public

    def start(self) -> None:
        self._listener = kb.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()

    def suppress(self, seconds: float = 0.5) -> None:
        """Ignore incoming key events for `seconds` (used during correction)."""
        import time

        def _clear():
            time.sleep(seconds)
            self._suppress_until.clear()

        self._suppress_until.set()
        t = threading.Thread(target=_clear, daemon=True)
        t.start()

    # ----------------------------------------------------------------- private

    def _on_press(self, key: kb.Key | kb.KeyCode) -> None:
        if self._suppress_until.is_set():
            return

        if key == kb.Key.backspace:
            self._on_backspace()
            return

        if key in _BOUNDARY_SPECIAL:
            char = {kb.Key.space: ' ', kb.Key.enter: '\n', kb.Key.tab: '\t'}[key]
            self._on_boundary(char)
            return

        # Printable character
        try:
            char = key.char
        except AttributeError:
            return  # modifier / function key

        if char and char.isprintable():
            if char in _BOUNDARY_CHARS:
                self._on_boundary(char)
            else:
                self._on_char(char)
