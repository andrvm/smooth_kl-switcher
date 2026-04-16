#!/usr/bin/env python3
"""smooth_kl-switcher — automatic keyboard layout correction for Linux."""

import sys
import os
import threading

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QTimer

from listener import KeyboardListener
from detector import check_word, script_of
from corrector import convert_en_to_ru, convert_ru_to_en
from layout import get_layout, switch_layout, is_wayland
from injector import replace_text


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

    def _on_boundary(self, boundary_char: str) -> None:
        with self._lock:
            word = ''.join(self._buf)
            self._buf.clear()

        self._try_correct(word, boundary_char)

    def _on_backspace(self) -> None:
        with self._lock:
            if self._buf:
                self._buf.pop()

    # ── correction ───────────────────────────────────────────────────────────

    def _try_correct(self, word: str, boundary_char: str) -> None:
        if not word or self._correcting:
            return

        current_layout = get_layout()
        result = check_word(word, current_layout)
        if result is None:
            return

        target_layout, corrected = result
        self._apply_correction(
            delete_count=len(word) + 1,    # word + boundary char already typed
            new_text=corrected + boundary_char,
            target_layout=target_layout,
        )

    def correct_current_word(self) -> None:
        """Manual trigger: correct whatever is in the buffer right now."""
        with self._lock:
            word = ''.join(self._buf)
            if not word:
                return
            self._buf.clear()

        scr = script_of(word)
        if scr == 'en':
            corrected, target = convert_en_to_ru(word), 'ru'
        elif scr == 'ru':
            corrected, target = convert_ru_to_en(word), 'en'
        else:
            return

        self._apply_correction(
            delete_count=len(word),
            new_text=corrected,
            target_layout=target,
        )

    def _apply_correction(self, delete_count: int, new_text: str,
                          target_layout: str) -> None:
        self._correcting = True
        self._listener.suppress(seconds=0.6)
        try:
            replace_text(delete_count, new_text, target_layout,
                         wayland=self._wayland)
        finally:
            self._correcting = False


# ─────────────────────────────────────────── entry point

def main() -> None:
    wayland = is_wayland()

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

    # ── start listener ────────────────────────────────────────────────────────
    try:
        switcher.start()
    except Exception as exc:
        tray.setIcon(_make_icon('!', '#d32f2f'))
        tray.setToolTip(f'smooth_kl-switcher — error: {exc}')
        tray.showMessage('smooth_kl-switcher', str(exc),
                         QSystemTrayIcon.MessageIcon.Critical)

    app.aboutToQuit.connect(switcher.stop)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
