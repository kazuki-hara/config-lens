"""アプリのメインフレームモジュール。

Config Lens アプリのルートウィンドウを定義する。
ナビゲーションバー（左列）とコンテンツエリア（右列）を配置し、
ビュー間の切り替えを管理する。
"""

import customtkinter as ctk

from src.compare.settings import AppSettings
from src.compare.view import CompareView
from src.menu import NavigationFrame


class DiffViewerApp(ctk.CTk):
    """Config Lens アプリのメインウィンドウ。

    左列にナビゲーションバー、右列にアクティブなビューを配置する。
    現在は比較ビュー（``CompareView``）のみ実装されており、
    将来的な機能追加にはナビゲーションバーにボタンを追加し、
    対応するビューをコンテンツエリアに配置する。
    """

    def __init__(self) -> None:
        super().__init__()

        self.title("Config Lens")
        self.geometry("1400x800")

        # アプリ共有設定
        self._settings = AppSettings()

        # ルートウィンドウの grid 設定
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)  # ナビゲーション（固定幅）
        self.grid_columnconfigure(1, weight=1)  # コンテンツエリア

        # --- 左側ナビゲーションバー ---
        self._nav_frame = NavigationFrame(
            self,
            on_compare=self._show_compare_view,
        )
        self._nav_frame.grid(row=0, column=0, sticky="nsew")

        # --- コンテンツエリア（右側）---
        self._compare_view = CompareView(self, self._settings)
        self._compare_view.grid(row=0, column=1, sticky="nsew")

    def _show_compare_view(self) -> None:
        """比較ビューを表示する。

        将来、複数の機能ビューを切り替える際に利用する。
        現時点では比較ビューのみのため、前面表示するだけ。
        """
        self._compare_view.tkraise()


def main() -> None:
    """アプリケーションのエントリーポイント。"""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = DiffViewerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
