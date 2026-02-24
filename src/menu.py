"""メインフレームのメニュー（ナビゲーションバー）モジュール。

アプリ左側に固定表示される縦型ナビゲーションバーを提供する。
新しい機能ビューを追加する場合は、対応するボタンをこのクラスに追加する。
"""

import importlib.metadata
from collections.abc import Callable

import customtkinter as ctk

# アプリバージョン
try:
    _APP_VERSION = f"v{importlib.metadata.version('01-config-lens')}"
except importlib.metadata.PackageNotFoundError:
    _APP_VERSION = "v0.2.0"

# ナビゲーションボタンの配色定数
_BTN_ACTIVE_FG = "#1f538d"
_BTN_ACTIVE_HOVER = "#2a6db5"
_BTN_INACTIVE_FG = "transparent"
_BTN_INACTIVE_HOVER = "#2a2a2a"


class NavigationFrame(ctk.CTkFrame):
    """アプリ左側に表示される縦型ナビゲーションバー。

    各機能への遷移ボタンを配置する。ボタンが押されると、対応する
    コールバックが呼ばれる。
    """

    def __init__(
        self,
        parent: ctk.CTk | ctk.CTkBaseClass,
        on_compare: Callable[[], None],
        on_validate: Callable[[], None],
    ) -> None:
        """初期化。

        Args:
            parent: 親ウィジェット
            on_compare: 「Text Diff Viewer」ボタン押下時のコールバック
            on_validate: 「Config Validator」ボタン押下時のコールバック
        """
        super().__init__(parent, width=160, corner_radius=0)
        self._on_compare = on_compare
        self._on_validate = on_validate
        self._nav_buttons: list[ctk.CTkButton] = []
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
        ).grid(row=0, column=0, padx=10, pady=(20, 2), sticky="ew")

        # バージョン表示
        ctk.CTkLabel(
            self,
            text=_APP_VERSION,
            font=ctk.CTkFont(size=10),
            text_color="#888888",
        ).grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # 区切り線
        ctk.CTkFrame(
            self, height=2, fg_color="#555555"
        ).grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))

        # セクションラベル
        ctk.CTkLabel(
            self,
            text="Menu",
            font=ctk.CTkFont(size=11),
            text_color="#888888",
            anchor="w",
        ).grid(row=3, column=0, padx=12, pady=(0, 4), sticky="ew")

        # Text Diff Viewer ボタン（初期アクティブ）
        self._nav_compare_btn = ctk.CTkButton(
            self,
            text="Text Diff Viewer",
            anchor="w",
            fg_color=_BTN_ACTIVE_FG,
            hover_color=_BTN_ACTIVE_HOVER,
            corner_radius=6,
            command=self._handle_compare,
        )
        self._nav_compare_btn.grid(
            row=4, column=0, padx=8, pady=3, sticky="ew"
        )

        # Config Validator ボタン（初期非アクティブ）
        self._nav_validate_btn = ctk.CTkButton(
            self,
            text="Config Validator",
            anchor="w",
            fg_color=_BTN_INACTIVE_FG,
            hover_color=_BTN_INACTIVE_HOVER,
            corner_radius=6,
            command=self._handle_validate,
        )
        self._nav_validate_btn.grid(
            row=5, column=0, padx=8, pady=3, sticky="ew"
        )

        self._nav_buttons = [
            self._nav_compare_btn,
            self._nav_validate_btn,
        ]

    def _set_active(self, active_btn: ctk.CTkButton) -> None:
        """指定ボタンをアクティブ表示にし、他を非アクティブにする。

        Args:
            active_btn: アクティブ状態にするボタン
        """
        for btn in self._nav_buttons:
            if btn is active_btn:
                btn.configure(
                    fg_color=_BTN_ACTIVE_FG,
                    hover_color=_BTN_ACTIVE_HOVER,
                )
            else:
                btn.configure(
                    fg_color=_BTN_INACTIVE_FG,
                    hover_color=_BTN_INACTIVE_HOVER,
                )

    def _handle_compare(self) -> None:
        """Text Diff Viewer ボタン押下時の処理。"""
        self._set_active(self._nav_compare_btn)
        self._on_compare()

    def _handle_validate(self) -> None:
        """Config Validator ボタン押下時の処理。"""
        self._set_active(self._nav_validate_btn)
        self._on_validate()
