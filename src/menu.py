"""メインフレームのメニュー（ナビゲーションバー）モジュール。

アプリ左側に固定表示される縦型ナビゲーションバーを提供する。
新しい機能ビューを追加する場合は、対応するボタンをこのクラスに追加する。
"""

from collections.abc import Callable

import customtkinter as ctk


class NavigationFrame(ctk.CTkFrame):
    """アプリ左側に表示される縦型ナビゲーションバー。

    各機能への遷移ボタンを配置する。ボタンが押されると、対応する
    コールバックが呼ばれる。
    """

    def __init__(
        self,
        parent: ctk.CTk | ctk.CTkBaseClass,
        on_compare: Callable[[], None],
    ) -> None:
        """初期化。

        Args:
            parent: 親ウィジェット
            on_compare: 「Compare Config Files」ボタン押下時のコールバック
        """
        super().__init__(parent, width=160, corner_radius=0)
        self._on_compare = on_compare
        self._create_widgets()

    def _create_widgets(self) -> None:
        """ウィジェットを構築する。"""
        self.grid_propagate(False)  # 固定幅を維持
        self.grid_rowconfigure(10, weight=1)  # 下部スペーサー
        self.grid_columnconfigure(0, weight=1)

        # アプリ名
        ctk.CTkLabel(
            self,
            text="Config Lens",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=(20, 10), sticky="ew")

        # 区切り線
        ctk.CTkFrame(
            self, height=2, fg_color="#555555"
        ).grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

        # セクションラベル
        ctk.CTkLabel(
            self,
            text="Menu",
            font=ctk.CTkFont(size=11),
            text_color="#888888",
            anchor="w",
        ).grid(row=2, column=0, padx=12, pady=(0, 4), sticky="ew")

        # 比較ボタン（アクティブ状態で表示）
        self._nav_compare_btn = ctk.CTkButton(
            self,
            text="Text Diff Viewer",
            anchor="w",
            fg_color="#1f538d",
            hover_color="#2a6db5",
            corner_radius=6,
            command=self._on_compare,
        )
        self._nav_compare_btn.grid(
            row=3, column=0, padx=8, pady=3, sticky="ew"
        )
