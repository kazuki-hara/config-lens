"""アプリのメインウィンドウモジュール。

TkinterDnD2 と customtkinter を統合した WinMerge ライクな
シングルビューアプリケーション。
"""

from __future__ import annotations

import importlib.metadata
import tkinter as tk

import customtkinter as ctk
from tkinterdnd2 import TkinterDnD

from src.compare.open_view import OpenView
from src.compare.settings import AppSettings

# バージョン文字列
try:
    _APP_VERSION = importlib.metadata.version("01-config-lens")
except importlib.metadata.PackageNotFoundError:
    _APP_VERSION = "0.3.0"


class DiffViewerApp(ctk.CTk, TkinterDnD.DnDWrapper):  # type: ignore[misc]
    """Config Lens メインウィンドウ。

    customtkinter の CTk に TkinterDnD のラッパーを混在させることで、
    ウィンドウ全体のドラッグ＆ドロップを有効化する。
    """

    def __init__(self) -> None:
        super().__init__()
        # tkdnd パッケージを要求してバージョンを保持
        self.TkdndVersion = TkinterDnD._require(self)  # type: ignore[attr-defined]

        self.title(f"Config Lens v{_APP_VERSION}")
        self.geometry("1400x800")
        self.minsize(900, 600)

        # アプリ共有設定
        self._settings = AppSettings()

        # ----- メニューバー -----
        self._build_menu()

        # ----- メインビュー -----
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._open_view = OpenView(self, self._settings)
        self._open_view.grid(row=0, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    # メニューバー構築
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        """tkinter Menu バーを構築する。"""
        menubar = tk.Menu(self, tearoff=False)

        # File メニュー
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(
            label="新しい比較 (Ctrl+N)",
            command=self._new_comparison,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="終了 (Ctrl+Q)",
            command=self.quit,
        )
        menubar.add_cascade(label="File", menu=file_menu)

        # Help メニュー
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(
            label=f"Config Lens について (v{_APP_VERSION})",
            command=self._show_about,
        )
        menubar.add_cascade(label="Help", menu=help_menu)

        self.configure(menu=menubar)

        # キーボードショートカット
        self.bind_all("<Control-n>", lambda _: self._new_comparison())
        self.bind_all("<Control-q>", lambda _: self.quit())

    # ------------------------------------------------------------------
    # メニューコールバック
    # ------------------------------------------------------------------

    def _new_comparison(self) -> None:
        """比較状態をリセットして新しい比較を開始できる状態にする。"""
        self._open_view.destroy()
        self._open_view = OpenView(self, self._settings)
        self._open_view.grid(row=0, column=0, sticky="nsew")

    def _show_about(self) -> None:
        """バージョン情報ダイアログを表示する。"""
        about_win = ctk.CTkToplevel(self)
        about_win.title("Config Lens について")
        about_win.geometry("320x180")
        about_win.resizable(False, False)
        about_win.transient(self)
        about_win.grab_set()

        ctk.CTkLabel(
            about_win,
            text="Config Lens",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(pady=(24, 4))
        ctk.CTkLabel(
            about_win,
            text=f"Version {_APP_VERSION}",
            font=ctk.CTkFont(size=13),
            text_color="#888888",
        ).pack()
        ctk.CTkLabel(
            about_win,
            text="ネットワーク機器コンフィグ比較ツール",
            font=ctk.CTkFont(size=11),
            text_color="#666666",
        ).pack(pady=(8, 0))
        ctk.CTkButton(
            about_win, text="閉じる", command=about_win.destroy, width=80
        ).pack(pady=16)


def main() -> None:
    """アプリケーションのエントリーポイント。"""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = DiffViewerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
