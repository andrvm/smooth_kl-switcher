#!/usr/bin/env python3
"""smooth_kl-switcher — automatic keyboard layout correction for Linux."""

import sys
import os
import shutil
import logging
import argparse
import threading

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt

from listener import KeyboardListener
from detector import check_word, script_of
from corrector import convert_en_to_ru, convert_ru_to_en
from layout import get_layout, switch_layout, is_wayland
from injector import replace_text

log = logging.getLogger('kl')


# ─────────────────────────────────────────── tray icon helpers

def _make_icon(text: str, bg: str = '#1a73e8') -> QIcon:
    px = QPixmap(64, 64)
    px.fill(QColor(bg))
    p = QPainter(px)
    p.setPen(QColor('#ffffff'))
    f = QFont('Sans', 22, QFont.Weight.Bold)
    p.setFont(f)
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, text)
    p.end()
    return QIcon(px)


# ─────────────────────────────────────────── core switcher

class Switcher:
    def __init__(self, wayland: bool) -> None:
        self._wayland = wayland
        self._buf: list[str] = []
        self._lock = threading.Lock()
        self._correcting = False

        self._listener = KeyboardListener(
            on_char=self._on_char,
            on_boundary=self._on_boundary,
            on_backspace=self._on_backspace,
        )

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()

    # ── keyboard callbacks (run in listener thread) ──────────────────────────

    def _on_char(self, char: str) -> None:
        with self._lock:
            self._buf.append(char)
        log.debug('char %r  buf=%r', char, ''.join(self._buf))

    def _on_boundary(self, boundary_char: str) -> None:
        with self._lock:
            word = ''.join(self._buf)
            self._buf.clear()
        log.debug('boundary %r  word=%r', boundary_char, word)
        self._try_correct(word, boundary_char)

    def _on_backspace(self) -> None:
        with self._lock:
            if self._buf:
                self._buf.pop()
        log.debug('backspace  buf=%r', ''.join(self._buf))

    # ── correction ───────────────────────────────────────────────────────────

    def _try_correct(self, word: str, boundary_char: str) -> None:
        # Skip Enter: in terminals/forms the action fires before we can undo it
        if not word or self._correcting or boundary_char == '\n':
            log.debug('skip: word=%r correcting=%s boundary=%r',
                      word, self._correcting, boundary_char)
            return

        current_layout = get_layout()
        log.debug('layout=%r  checking word=%r', current_layout, word)

        result = check_word(word, current_layout)
        log.debug('check_word → %r', result)

        if result is None:
            return

        target_layout, corrected = result
        log.info('AUTO  %r → %r  (layout %s → %s)',
                 word, corrected, current_layout, target_layout)
        threading.Thread(
            target=self._apply_correction,
            args=(len(word) + 1, corrected + boundary_char, target_layout),
            daemon=True,
        ).start()

    def correct_current_word(self) -> None:
        """Manual trigger: correct whatever is in the buffer right now."""
        with self._lock:
            word = ''.join(self._buf)
            if not word:
                log.debug('manual trigger: buffer empty')
                return
            self._buf.clear()

        current_layout = get_layout()
        log.debug('manual: layout=%r word=%r', current_layout, word)

        result = check_word(word, current_layout)
        if result is None:
            # Fallback: flip by script when auto-detect finds nothing
            scr = script_of(word)
            log.debug('manual fallback: script=%r', scr)
            if scr == 'en':
                result = ('ru', convert_en_to_ru(word))
            elif scr == 'ru':
                result = ('en', convert_ru_to_en(word))
            else:
                log.debug('manual: nothing to correct')
                return

        target_layout, corrected = result
        log.info('MANUAL  %r → %r  (layout %s → %s)',
                 word, corrected, current_layout, target_layout)
        self._apply_correction(
            delete_count=len(word),
            new_text=corrected,
            target_layout=target_layout,
        )

    def _apply_correction(self, delete_count: int, new_text: str,
                          target_layout: str) -> None:
        log.debug('inject: delete=%d  type=%r  layout→%s',
                  delete_count, new_text, target_layout)
        self._correcting = True
        self._listener.suppress(seconds=0.6)
        try:
            replace_text(delete_count, new_text, target_layout,
                         wayland=self._wayland)
            log.debug('inject done')
        except Exception as exc:
            log.error('inject failed: %s', exc)
        finally:
            self._correcting = False


# ─────────────────────────────────────────── entry point

def main() -> None:
    parser = argparse.ArgumentParser(description='smooth_kl-switcher')
    parser.add_argument('--debug', action='store_true',
                        help='Print verbose debug output to stdout')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format='%(asctime)s  %(levelname)-5s  %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stdout,
    )

    if args.debug:
        log.info('debug mode on')

    wayland = is_wayland()
    log.info('session: %s', 'wayland' if wayland else 'x11')

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    switcher = Switcher(wayland=wayland)

    # ── tray icon ─────────────────────────────────────────────────────────────
    tray = QSystemTrayIcon()
    tray.setIcon(_make_icon('KL'))
    tray.setToolTip('smooth_kl-switcher — running')

    menu = QMenu()

    status_label = f"{'Wayland' if wayland else 'X11'} — auto-correct ON"
    menu.addAction(status_label).setEnabled(False)
    menu.addSeparator()

    correct_action = menu.addAction('Correct current word  (Ctrl+Shift+Z)')
    correct_action.triggered.connect(switcher.correct_current_word)

    menu.addSeparator()
    quit_action = menu.addAction('Quit')
    quit_action.triggered.connect(app.quit)

    tray.setContextMenu(menu)
    tray.show()

    # ── global hotkey: Ctrl+Shift+Z ──────────────────────────────────────────
    try:
        from pynput import keyboard as kb

        def _on_hotkey():
            switcher.correct_current_word()

        hotkey = kb.GlobalHotKeys({'<ctrl>+<shift>+z': _on_hotkey})
        hotkey.daemon = True
        hotkey.start()
    except Exception:
        pass  # hotkey registration is best-effort

    # ── check required system tools ───────────────────────────────────────────
    from layout import _is_gnome
    layout_tool = 'gsettings' if (wayland and _is_gnome()) else 'setxkbmap'
    if not shutil.which(layout_tool):
        msg = f'{layout_tool} not found — layout detection disabled.'
        tray.setIcon(_make_icon('!', '#d32f2f'))
        tray.setToolTip(f'smooth_kl-switcher — {msg}')
        tray.showMessage('smooth_kl-switcher', msg,
                         QSystemTrayIcon.MessageIcon.Warning)

    # ── start listener ────────────────────────────────────────────────────────
    try:
        switcher.start()
        log.info('listener started')
    except Exception as exc:
        tray.setIcon(_make_icon('!', '#d32f2f'))
        tray.setToolTip(f'smooth_kl-switcher — error: {exc}')
        tray.showMessage('smooth_kl-switcher', str(exc),
                         QSystemTrayIcon.MessageIcon.Critical)
        log.error('listener failed: %s', exc)

    app.aboutToQuit.connect(switcher.stop)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
