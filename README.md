# smooth_kl-switcher

A Linux desktop app that detects when you're typing in the wrong keyboard layout and silently corrects it.

## The problem

You press the hotkey to switch from English to Russian (or back). Sometimes the switch glitches and doesn't register. You type a whole word before noticing — `ghbdtn` instead of `привет`, or `руддщ` instead of `hello`.

smooth_kl-switcher watches your typing and fixes these mistakes automatically.

## How it works

After each word (space / Enter / Tab), the app checks whether the typed characters look like wrong-layout text:

- Latin word typed while the layout is set to Russian → converts via EN→RU key map and switches layout
- Latin word with unusual consonant clusters or Russian-specific key patterns (e.g. `ghbdtn`, `tdjq`) → auto-corrects even when the layout hasn't visibly changed yet
- Cyrillic word typed while the layout is set to English → converts via RU→EN key map

If a match is found, the app silently erases the word and re-types the corrected version in the right layout.

## Requirements

**Python dependencies** (installed automatically by `build.sh`):

```
pynput
PyQt6
pyinstaller
```

**System tools** (install via your package manager):

| Tool | Purpose | Install |
|---|---|---|
| `xdotool` | Type text and send keys | `apt install xdotool` |
| `xkb-switch` | Query and switch keyboard layout | `apt install xkb-switch` |
| `ydotool` | Text injection on Wayland (optional) | `apt install ydotool` |

Arch: `pacman -S xdotool xkb-switch`  
Fedora: `dnf install xdotool xkb-switch`

## Installation

```bash
git clone https://github.com/andrvm/smooth_kl-switcher.git
cd smooth_kl-switcher
bash build.sh
```

This produces a single self-contained binary at `dist/smooth_kl-switcher`.

To run at startup, copy it to `~/.local/bin/` and add it to your desktop environment's autostart.

## Usage

```bash
./dist/smooth_kl-switcher
```

A tray icon (`KL`) appears in the system tray. The app runs silently in the background.

### Manual correction

If auto-correction doesn't trigger, you can force it:

- **Keyboard:** `Ctrl+Shift+Z` — corrects whatever you just typed
- **Tray menu:** right-click the tray icon → *Correct current word*

### Quitting

Right-click the tray icon → *Quit*.

## Keyboard layout support

Currently supports the standard **Russian QWERTY** layout (the default on Windows and most Linux distros). The full key map:

| Physical key | English | Russian |
|---|---|---|
| Q | q | й |
| W | w | ц |
| E | e | у |
| R | r | к |
| T | t | е |
| Y | y | н |
| U | u | г |
| I | i | ш |
| O | o | щ |
| P | p | з |
| A | a | ф |
| S | s | ы |
| D | d | в |
| F | f | а |
| G | g | п |
| H | h | р |
| J | j | о |
| K | k | л |
| L | l | д |
| Z | z | я |
| X | x | ч |
| C | c | с |
| V | v | м |
| B | b | и |
| N | n | т |
| M | m | ь |

## Display server support

| Session | Status |
|---|---|
| X11 | Full support |
| Wayland | Partial — keyboard monitoring works; text injection requires `ydotool` |

The app detects your session type automatically via `$WAYLAND_DISPLAY`.

## Project structure

```
smooth_kl-switcher/
├── main.py          # Entry point — system tray, word buffer, hotkey
├── listener.py      # Keyboard monitoring (pynput)
├── detector.py      # Wrong-layout detection heuristics
├── corrector.py     # EN↔RU character mapping tables
├── layout.py        # Query and switch keyboard layout
├── injector.py      # Erase and retype text (xdotool / ydotool)
├── requirements.txt
└── build.sh         # Builds dist/smooth_kl-switcher via PyInstaller
```

## License

MIT
