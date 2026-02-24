"""アプリのメインフレームモジュール。

Config Lens アプリのルートウィンドウを定義する。
ナビゲーションバー（左列）とコンテンツエリア（右列）を配置し、
ビュー間の切り替えを管理する。
"""

import customtkinter as ctk

from src.compare.settings import AppSettings
from src.compare.view import CompareView
from src.menu import NavigationFrame
from src.validate.view import ValidateView


class DiffViewerApp(ctk.CTk):
    """Config Lens アプリのメインウィンドウ。

    左列にナビゲーションバー、右列にアクティブなビューを配置する。
    ナビゲーションバーのボタン押下に応じて、コンテンツエリアに
    表示するビューを切り替える。
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
            on_validate=self._show_validate_view,
        )
        self._nav_frame.grid(row=0, column=0, sticky="nsew")

        # --- コンテンツエリア（右側）---
        # 複数ビューを同じセルに積み重ねて tkraise() で切り替える
        self._compare_view = CompareView(self, self._settings)
        self._compare_view.grid(row=0, column=1, sticky="nsew")

        self._validate_view = ValidateView(self)
        self._validate_view.grid(row=0, column=1, sticky="nsew")

        # 起動時は比較ビューを前面表示
        self._show_compare_view()

    def _show_compare_view(self) -> None:
        """Text Diff Viewer ビューを前面に表示する。"""
        self._compare_view.tkraise()

    def _show_validate_view(self) -> None:
        """Config Validator ビューを前面に表示する。"""
        self._validate_view.tkraise()


def main() -> None:
    """アプリケーションのエントリーポイント。"""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = DiffViewerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
