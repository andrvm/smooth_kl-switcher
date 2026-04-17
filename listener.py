import threading
import logging
from typing import Callable

from evdev import InputDevice, ecodes, categorize, KeyEvent
import evdev

from corrector import KEY_EN, KEY_RU
from layout import get_layout_cached

log = logging.getLogger('kl.listener')

# Physical keycode → lowercase char for each layout
_EN_CODE_TO_CHAR: dict[int, str] = {}
_RU_CODE_TO_CHAR: dict[int, str] = {}

for _name, _char in KEY_EN.items():
    _code = getattr(ecodes, _name, None)
    if _code is not None:
        _EN_CODE_TO_CHAR[_code] = _char

for _name, _char in KEY_RU.items():
    _code = getattr(ecodes, _name, None)
    if _code is not None:
        _RU_CODE_TO_CHAR[_code] = _char

_SHIFT_CODES = {ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT}
_BOUNDARY_CHAR = {
    ecodes.KEY_SPACE: ' ',
    ecodes.KEY_TAB: '\t',
    ecodes.KEY_ENTER: '\n',
}


def _find_keyboards() -> list[InputDevice]:
    keyboards = []
    for path in evdev.list_devices():
        try:
            dev = InputDevice(path)
            caps = dev.capabilities()
            if (ecodes.EV_KEY in caps
                    and ecodes.KEY_A in caps[ecodes.EV_KEY]
                    and ecodes.KEY_SPACE in caps[ecodes.EV_KEY]):
                keyboards.append(dev)
        except (OSError, PermissionError):
            pass
    return keyboards


class KeyboardListener:
    """
    Listens to keyboard events via evdev and exposes three callbacks:
      on_char(char)          — a printable character was typed
      on_boundary(char)      — a word-boundary key was pressed (space/tab/enter)
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
        self._suppress_until = threading.Event()
        self._shift_held = False
        self._devices: list[InputDevice] = []

    # ------------------------------------------------------------------ public

    def start(self) -> None:
        self._devices = _find_keyboards()
        if not self._devices:
            raise RuntimeError(
                'No keyboard devices found under /dev/input/. '
                'Run via:  sg input -c "venv/bin/python main.py"  '
                'or log out and back in after: sudo usermod -aG input $USER'
            )
        log.debug('found %d keyboard device(s): %s',
                  len(self._devices), [d.path for d in self._devices])
        for dev in self._devices:
            t = threading.Thread(target=self._read_device, args=(dev,),
                                 daemon=True)
            t.start()

    def stop(self) -> None:
        for dev in self._devices:
            try:
                dev.close()
            except Exception:
                pass

    def suppress(self, seconds: float = 0.5) -> None:
        """Ignore incoming key events for `seconds` (used during correction)."""
        import time

        def _clear():
            time.sleep(seconds)
            self._suppress_until.clear()

        self._suppress_until.set()
        threading.Thread(target=_clear, daemon=True).start()

    # ----------------------------------------------------------------- private

    def _read_device(self, dev: InputDevice) -> None:
        try:
            for event in dev.read_loop():
                if self._suppress_until.is_set():
                    continue
                if event.type != ecodes.EV_KEY:
                    continue
                key_ev = categorize(event)
                # key_down=1, key_hold=2 (only use hold for backspace repeat)
                if key_ev.keystate == KeyEvent.key_up:
                    continue
                if key_ev.keystate == KeyEvent.key_hold and \
                        key_ev.scancode != ecodes.KEY_BACKSPACE:
                    continue
                self._handle_key(key_ev.scancode, key_ev.keystate)
        except (OSError, IOError):
            log.debug('device closed: %s', dev.path)

    def _handle_key(self, keycode: int, keystate: int) -> None:
        # Track shift state
        if keycode in _SHIFT_CODES:
            self._shift_held = (keystate == KeyEvent.key_down)
            return

        if keycode == ecodes.KEY_BACKSPACE:
            self._on_backspace()
            return

        boundary_char = _BOUNDARY_CHAR.get(keycode)
        if boundary_char is not None:
            self._on_boundary(boundary_char)
            return

        # Translate keycode → character using cached layout
        layout = get_layout_cached()
        char_map = _RU_CODE_TO_CHAR if layout == 'ru' else _EN_CODE_TO_CHAR
        char = char_map.get(keycode)
        if char is None:
            return  # number, function key, etc.
        if self._shift_held:
            char = char.upper()
        self._on_char(char)
