"""比較機能のIgnoreパターン管理モジュール。

パターンはアプリ共通の設定ファイル（settings.json）の
``compare.ignore.patterns`` セクションに保存される。
"""

import re

import customtkinter as ctk

from src.compare.settings import AppSettings

# AppSettings 上のセクションパス
_SECTION: list[str] = ["compare", "ignore", "patterns"]


class IgnorePatternManager:
    """Ignore対象の正規表現パターンを管理するクラス。

    パターンは ``AppSettings`` を通じてアプリ共有の設定ファイルに保存され、
    アプリ再起動後も維持される。他機能の設定も同一JSONファイルに共存できる。
    """

    def __init__(self, settings: AppSettings) -> None:
        self._settings: AppSettings = settings
        self._patterns: list[str] = []
        self._compiled: list[re.Pattern[str]] = []
        self._load()

    # ------------------------------------------------------------------
    # 永続化
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """設定ファイルからパターンを読み込む。"""
        raw = self._settings.get(*_SECTION, default=[])
        if not isinstance(raw, list):
            return
        compiled: list[re.Pattern[str]] = []
        valid: list[str] = []
        for p in raw:
            if not isinstance(p, str):
                continue
            try:
                compiled.append(re.compile(p))
                valid.append(p)
            except re.error:
                pass  # 無効なパターンは読み飛ばす
        self._patterns = valid
        self._compiled = compiled

    def _save(self) -> None:
        """パターンを設定ファイルに保存する。"""
        self._settings.update(_SECTION, self._patterns)

    # ------------------------------------------------------------------
    # パターン操作
    # ------------------------------------------------------------------

    def get_patterns(self) -> list[str]:
        """登録済みパターンのリストを返す（コピー）。"""
        return list(self._patterns)

    def add_pattern(self, pattern: str) -> None:
        """パターンを追加して保存する。

        Args:
            pattern: 追加する正規表現文字列（前後の空白は除去される）

        Raises:
            ValueError: 空文字列または重複パターンの場合
            re.error: 無効な正規表現の場合
        """
        pattern = pattern.strip()
        if not pattern:
            raise ValueError("パターンが空です")
        if pattern in self._patterns:
            raise ValueError(f"'{pattern}' は既に登録されています")
        compiled = re.compile(pattern)  # 無効な正規表現は re.error を送出
        self._patterns.append(pattern)
        self._compiled.append(compiled)
        self._save()

    def remove_pattern(self, pattern: str) -> None:
        """パターンを削除して保存する。

        Args:
            pattern: 削除するパターン文字列
        """
        if pattern in self._patterns:
            idx = self._patterns.index(pattern)
            self._patterns.pop(idx)
            self._compiled.pop(idx)
            self._save()

    # ------------------------------------------------------------------
    # マッチング
    # ------------------------------------------------------------------

    def matches(self, line: str) -> bool:
        """行テキストがいずれかのパターンにマッチするか判定する。

        Args:
            line: 判定対象の行テキスト

        Returns:
            いずれかのパターンにマッチした場合 ``True``。
        """
        return any(compiled.search(line) for compiled in self._compiled)

    # ------------------------------------------------------------------
    # プロパティ
    # ------------------------------------------------------------------

    @property
    def settings_path(self) -> object:
        """設定ファイルの絶対パスを返す。"""
        return self._settings.settings_path


class IgnorePatternDialog(ctk.CTkToplevel):
    """Ignoreパターンを管理するダイアログウィンドウ。

    登録済みパターンの一覧表示・追加・削除を行う。
    設定はOS標準のユーザーデータディレクトリに自動保存される。
    """

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        manager: IgnorePatternManager,
    ) -> None:
        super().__init__(parent)
        self._manager = manager
        self.title("Ignoreパターン管理")
        self.geometry("560x440")
        self.resizable(True, True)
        self.transient(parent)  # type: ignore[arg-type]
        self.grab_set()
        self._create_widgets()

    def _create_widgets(self) -> None:
        """ウィジェットを構築する。"""
        # 追加エリア
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            add_frame, text="正規表現:"
        ).pack(side="left", padx=(5, 2))

        self._entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="例: ^!.*  /  ^Building.*  /  NTP.*",
        )
        self._entry.pack(side="left", expand=True, fill="x", padx=5)
        self._entry.bind("<Return>", lambda _: self._add_pattern())

        ctk.CTkButton(
            add_frame,
            text="追加",
            command=self._add_pattern,
            width=70,
        ).pack(side="left", padx=5)

        # エラーラベル
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#ff6b6b"
        )
        self._error_label.pack(pady=(0, 4))

        # パターンリスト（スクロール可能）
        self._list_frame = ctk.CTkScrollableFrame(
            self, label_text="登録済みパターン"
        )
        self._list_frame.pack(
            fill="both", expand=True, padx=10, pady=(0, 8)
        )

        # 設定ファイルパス表示
        path_text = f"設定: {self._manager.settings_path}"
        ctk.CTkLabel(
            self,
            text=path_text,
            font=ctk.CTkFont(size=10),
            text_color="#888888",
        ).pack(pady=(0, 6))

        self._refresh_list()

    def _refresh_list(self) -> None:
        """パターンリストを再描画する。"""
        for widget in self._list_frame.winfo_children():
            widget.destroy()

        patterns = self._manager.get_patterns()
        if not patterns:
            ctk.CTkLabel(
                self._list_frame,
                text="登録済みパターンはありません",
                text_color="#666666",
            ).pack(pady=10)
            return

        for pattern in patterns:
            row = ctk.CTkFrame(self._list_frame)
            row.pack(fill="x", pady=2, padx=2)

            ctk.CTkLabel(
                row,
                text=pattern,
                anchor="w",
                font=ctk.CTkFont(family="Courier", size=11),
            ).pack(side="left", expand=True, fill="x", padx=8)

            ctk.CTkButton(
                row,
                text="削除",
                width=55,
                fg_color="#6b2020",
                hover_color="#8b0000",
                command=lambda p=pattern: self._remove_pattern(p),  # type: ignore[misc]
            ).pack(side="right", padx=5, pady=3)

    def _add_pattern(self) -> None:
        """入力欄のパターンを追加する。"""
        pattern = self._entry.get()
        try:
            self._manager.add_pattern(pattern)
            self._entry.delete(0, "end")
            self._error_label.configure(text="")
            self._refresh_list()
        except re.error as e:
            self._error_label.configure(text=f"正規表現エラー: {e}")
        except ValueError as e:
            self._error_label.configure(text=str(e))

    def _remove_pattern(self, pattern: str) -> None:
        """指定パターンを削除する。

        Args:
            pattern: 削除するパターン文字列
        """
        self._manager.remove_pattern(pattern)
        self._refresh_list()
