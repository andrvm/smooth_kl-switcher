import time

from evdev import ecodes

from layout import switch_layout
from corrector import KEY_EN, KEY_RU

# evdev keycode offset to X11 keycode (Linux standard: x11 = evdev + 8)
_X11_OFFSET = 8

# Build physical-key name → evdev keycode
_KEY_TO_CODE: dict[str, int] = {}
for _name in KEY_EN:
    _code = getattr(ecodes, _name, None)
    if _code is not None:
        _KEY_TO_CODE[_name] = _code

# char → (evdev_keycode, needs_shift) for each layout
_EN_CHAR_TO_KEY: dict[str, tuple[int, bool]] = {}
_RU_CHAR_TO_KEY: dict[str, tuple[int, bool]] = {}

for _key_name, _char in KEY_EN.items():
    _code = _KEY_TO_CODE.get(_key_name)
    if _code is not None:
        _EN_CHAR_TO_KEY[_char] = (_code, False)
        _EN_CHAR_TO_KEY[_char.upper()] = (_code, True)

for _key_name, _char in KEY_RU.items():
    _code = _KEY_TO_CODE.get(_key_name)
    if _code is not None:
        _RU_CHAR_TO_KEY[_char] = (_code, False)
        _RU_CHAR_TO_KEY[_char.upper()] = (_code, True)

_UINPUT_CAPABILITIES = {
    ecodes.EV_KEY: sorted({
        ecodes.KEY_BACKSPACE,
        ecodes.KEY_SPACE,
        ecodes.KEY_ENTER,
        ecodes.KEY_TAB,
        ecodes.KEY_LEFTSHIFT,
        *_KEY_TO_CODE.values(),
    })
}


# ── X11 injection via XTest (no special permissions needed) ──────────────────

def _inject_x11(delete_count: int, new_text: str,
                char_map: dict[str, tuple[int, bool]]) -> None:
    from Xlib import display as xdisplay, X
    from Xlib.ext import xtest

    d = xdisplay.Display()
    shift_kc = d.keysym_to_keycode(0xffe1)  # XK_Shift_L

    def tap(evdev_kc: int, shift: bool = False) -> None:
        x11_kc = evdev_kc + _X11_OFFSET
        if shift:
            xtest.fake_input(d, X.KeyPress, shift_kc)
        xtest.fake_input(d, X.KeyPress, x11_kc)
        xtest.fake_input(d, X.KeyRelease, x11_kc)
        if shift:
            xtest.fake_input(d, X.KeyRelease, shift_kc)
        d.flush()

    for _ in range(delete_count):
        tap(ecodes.KEY_BACKSPACE)
    for char in new_text:
        if char == '\n':
            tap(ecodes.KEY_ENTER)
        elif char == '\t':
            tap(ecodes.KEY_TAB)
        elif char == ' ':
            tap(ecodes.KEY_SPACE)
        else:
            entry = char_map.get(char)
            if entry:
                tap(entry[0], entry[1])

    d.close()


# ── Wayland injection via evdev UInput (requires input group) ────────────────

def _inject_uinput(delete_count: int, new_text: str,
                   char_map: dict[str, tuple[int, bool]]) -> None:
    from evdev import UInput

    with UInput(_UINPUT_CAPABILITIES, name='smooth-kl-switcher') as ui:
        time.sleep(0.02)  # let udev register the virtual device

        def tap(keycode: int, shift: bool = False) -> None:
            if shift:
                ui.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 1)
                ui.syn()
            ui.write(ecodes.EV_KEY, keycode, 1)
            ui.syn()
            ui.write(ecodes.EV_KEY, keycode, 0)
            ui.syn()
            if shift:
                ui.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 0)
                ui.syn()

        for _ in range(delete_count):
            tap(ecodes.KEY_BACKSPACE)
        for char in new_text:
            if char == '\n':
                tap(ecodes.KEY_ENTER)
            elif char == '\t':
                tap(ecodes.KEY_TAB)
            elif char == ' ':
                tap(ecodes.KEY_SPACE)
            else:
                entry = char_map.get(char)
                if entry:
                    tap(entry[0], entry[1])


# ── public entry point ────────────────────────────────────────────────────────

def replace_text(delete_count: int, new_text: str, target_layout: str,
                 wayland: bool = False) -> None:
    """Delete delete_count chars then type new_text in target_layout."""
    switch_layout(target_layout)
    time.sleep(0.05)  # let the layout switch settle

    char_map = _RU_CHAR_TO_KEY if target_layout == 'ru' else _EN_CHAR_TO_KEY

    if wayland:
        _inject_uinput(delete_count, new_text, char_map)
    else:
        _inject_x11(delete_count, new_text, char_map)
