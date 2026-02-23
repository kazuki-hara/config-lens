import difflib
import re
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from hier_config import Platform

try:
    from src.diff import TextAlignedDiffComparator
    from src.ignore import IgnorePatternManager
except ModuleNotFoundError:
    from diff import TextAlignedDiffComparator
    from ignore import IgnorePatternManager

# 文字単位インライン差分の設定
_INLINE_DIFF_THRESHOLD: float = 0.4  # ペアリングに必要な最低類似度
_LINE_NUM_WIDTH: int = 5  # 行番号プレフィックスの文字数 ("   1 ")

# Platform名とPlatform列挙型のマッピング
_PLATFORM_MAP: dict[str, Platform] = {
    "CISCO_IOS": Platform.CISCO_IOS,
    "CISCO_NXOS (Not Supported)": Platform.CISCO_NXOS,
    "CISCO_XR (Not Supported)": Platform.CISCO_XR,
    "ARISTA_EOS (Not Supported)": Platform.ARISTA_EOS,
    "JUNIPER_JUNOS (Not Supported)": Platform.JUNIPER_JUNOS,
    "FORTINET_FORTIOS (Not Supported)": Platform.FORTINET_FORTIOS,
    "HP_COMWARE5 (Not Supported)": Platform.HP_COMWARE5,
    "HP_PROCURVE (Not Supported)": Platform.HP_PROCURVE,
    "VYOS (Not Supported)": Platform.VYOS,
    "GENERIC (Not Supported)": Platform.GENERIC,
}


class DiffViewerApp(ctk.CTk):
    """テキストファイルの差分を2列で比較表示するGUIアプリケーション"""

    def __init__(self):
        super().__init__()

        # ウィンドウの設定
        self.title("Config Lens - Text Diff Viewer")
        self.geometry("1400x800")

        # ファイルパスを保持
        self.source_file_path: str = ""
        self.target_file_path: str = ""

        # 比較結果のキー情報（クリックジャンプ用）
        # キー: 階層パスキー文字列、値: 1ベースの行番号
        self._src_key_to_row: dict[str, int] = {}
        self._tgt_key_to_row: dict[str, int] = {}
        self._src_types: list[str] = []
        self._tgt_types: list[str] = []
        self._src_keys: list[str] = []
        self._tgt_keys: list[str] = []

        # 現在アクティブなreorder強調表示の行番号（1ベース）
        self._active_src_row: int = -1
        self._active_tgt_row: int = -1

        # Ignore機能
        self._ignore_manager: IgnorePatternManager = IgnorePatternManager()
        self._ignore_enabled_var: tk.BooleanVar = tk.BooleanVar(value=True)
        self._ignore_dialog: "IgnorePatternDialog | None" = None

        # UIの構築
        self._create_widgets()

    def _create_widgets(self) -> None:
        """UIウィジェットを作成"""
        # トップフレーム（ファイル選択ボタン）
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        # 左側のファイル選択
        left_file_frame = ctk.CTkFrame(top_frame)
        left_file_frame.pack(side="left", expand=True, fill="x", padx=5)

        self.source_label = ctk.CTkLabel(
            left_file_frame,
            text="ソースファイル: 未選択",
            anchor="w"
        )
        self.source_label.pack(side="left", expand=True, fill="x", padx=5)

        source_button = ctk.CTkButton(
            left_file_frame,
            text="ソースファイルを開く",
            command=self._open_source_file,
            width=150
        )
        source_button.pack(side="right", padx=5)

        # 右側のファイル選択
        right_file_frame = ctk.CTkFrame(top_frame)
        right_file_frame.pack(side="left", expand=True, fill="x", padx=5)

        self.target_label = ctk.CTkLabel(
            right_file_frame,
            text="ターゲットファイル: 未選択",
            anchor="w"
        )
        self.target_label.pack(side="left", expand=True, fill="x", padx=5)

        target_button = ctk.CTkButton(
            right_file_frame,
            text="ターゲットファイルを開く",
            command=self._open_target_file,
            width=150
        )
        target_button.pack(side="right", padx=5)

        # Platformセレクタ
        platform_frame = ctk.CTkFrame(top_frame)
        platform_frame.pack(side="left", padx=5)

        ctk.CTkLabel(
            platform_frame,
            text="Platform:"
        ).pack(side="left", padx=(5, 2))

        self.platform_combobox = ctk.CTkComboBox(
            platform_frame,
            values=list(_PLATFORM_MAP.keys()),
            width=160,
            state="readonly",
        )
        self.platform_combobox.set("CISCO_IOS")
        self.platform_combobox.pack(side="left", padx=(0, 5))

        # 比較ボタン
        compare_button = ctk.CTkButton(
            top_frame,
            text="比較",
            command=self._compare_files,
            width=100,
            fg_color="green",
            hover_color="darkgreen"
        )
        compare_button.pack(side="left", padx=10)

        # Ignoreパターン管理ボタン + 有効/無効トグル
        ignore_frame = ctk.CTkFrame(top_frame)
        ignore_frame.pack(side="left", padx=5)

        ctk.CTkButton(
            ignore_frame,
            text="Ignoreパターン管理",
            command=self._open_ignore_dialog,
            width=160,
        ).pack(side="left", padx=(5, 8))

        self._ignore_switch = ctk.CTkSwitch(
            ignore_frame,
            text="Ignore有効",
            variable=self._ignore_enabled_var,
            onvalue=True,
            offvalue=False,
        )
        self._ignore_switch.pack(side="left", padx=5)

        # メインフレーム（テキスト表示エリア）
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 左側のテキストエリア
        left_text_frame = ctk.CTkFrame(main_frame)
        left_text_frame.pack(side="left", expand=True, fill="both", padx=5)

        left_header = ctk.CTkLabel(
            left_text_frame,
            text="ソース",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        left_header.pack(pady=5)

        self.source_text = tk.Text(
            left_text_frame,
            wrap="none",
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="#ffffff",
            font=("Courier", 11),
            cursor="arrow",
        )
        self.source_text.pack(side="left", expand=True, fill="both")
        self.source_text.bind("<Button-1>", self._on_source_click)

        source_scrollbar = ctk.CTkScrollbar(
            left_text_frame,
            command=self._on_scroll
        )
        source_scrollbar.pack(side="right", fill="y")
        self.source_text.config(yscrollcommand=source_scrollbar.set)

        # 右側のテキストエリア
        right_text_frame = ctk.CTkFrame(main_frame)
        right_text_frame.pack(side="left", expand=True, fill="both", padx=5)

        right_header = ctk.CTkLabel(
            right_text_frame,
            text="ターゲット",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        right_header.pack(pady=5)

        self.target_text = tk.Text(
            right_text_frame,
            wrap="none",
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="#ffffff",
            font=("Courier", 11),
            cursor="arrow",
        )
        self.target_text.pack(side="left", expand=True, fill="both")
        self.target_text.bind("<Button-1>", self._on_target_click)

        target_scrollbar = ctk.CTkScrollbar(
            right_text_frame,
            command=self._on_scroll
        )
        target_scrollbar.pack(side="right", fill="y")
        self.target_text.config(yscrollcommand=target_scrollbar.set)

        # タグの設定（差分の色分け）
        self._configure_tags()

        # ステータスバー
        self.status_bar = ctk.CTkLabel(
            self,
            text="ファイルを選択して比較を開始してください",
            anchor="w"
        )
        self.status_bar.pack(fill="x", padx=10, pady=(0, 5))

    def _configure_tags(self) -> None:
        """テキストウィジェットのタグを設定"""
        # 削除された行（sourceのみに存在）
        self.source_text.tag_configure(
            "delete",
            background="#4d1f1f",
            foreground="#ff6b6b"
        )

        # 挿入された行（targetのみに存在）
        self.target_text.tag_configure(
            "insert",
            background="#1f4d1f",
            foreground="#6bff6b"
        )

        # 順番違い（両方に存在するが順番が異なる）
        for widget in (self.source_text, self.target_text):
            widget.tag_configure(
                "reorder",
                background="#4d3b1f",
                foreground="#ffb347"
            )
            # クリック時の強調表示
            widget.tag_configure(
                "reorder_active",
                background="#7a5a1a",
                foreground="#ffe680"
            )

        # 空行（対応する行がない側のパディング）
        self.source_text.tag_configure("empty", background="#1a1a1a")
        self.target_text.tag_configure("empty", background="#1a1a1a")

        # 文字単位差分強調（delete行内の変更文字 / insert行内の変更文字）
        self.source_text.tag_configure(
            "delete_char", background="#8b0000", foreground="#ffffff"
        )
        self.target_text.tag_configure(
            "insert_char", background="#006400", foreground="#ffffff"
        )

        # Ignore行（差分があっても検知対象外とした行）
        for widget in (self.source_text, self.target_text):
            widget.tag_configure(
                "ignore",
                background="#2f2f2f",
                foreground="#5a5a5a",
            )

        # タグ優先順位:
        #   reorder_active > delete_char/insert_char
        #   > ignore > reorder > delete/insert > empty
        for widget in (self.source_text, self.target_text):
            widget.tag_raise("reorder_active")
        self.source_text.tag_raise("delete_char")
        self.target_text.tag_raise("insert_char")

    def _apply_char_diff(self, src_row: int, tgt_row: int, src_line: str, tgt_line: str) -> None:
        """2行間の文字単位差分を強調表示する

        Args:
            src_row (int): source側の行番号（1ベース）
            tgt_row (int): target側の行番号（1ベース）
            src_line (str): source側の行テキスト（行番号プレフィックスなし）
            tgt_line (str): target側の行テキスト（行番号プレフィックスなし）
        """
        matcher = difflib.SequenceMatcher(None, src_line, tgt_line, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in ("replace", "delete"):
                self.source_text.tag_add(
                    "delete_char",
                    f"{src_row}.{i1 + _LINE_NUM_WIDTH}",
                    f"{src_row}.{i2 + _LINE_NUM_WIDTH}",
                )
            if tag in ("replace", "insert"):
                self.target_text.tag_add(
                    "insert_char",
                    f"{tgt_row}.{j1 + _LINE_NUM_WIDTH}",
                    f"{tgt_row}.{j2 + _LINE_NUM_WIDTH}",
                )

    def _open_ignore_dialog(self) -> None:
        """Ignoreパターン管理ダイアログを開く。

        既に開いている場合は前面に移動する。
        """
        if (
            self._ignore_dialog is not None
            and self._ignore_dialog.winfo_exists()
        ):
            self._ignore_dialog.lift()
            return
        self._ignore_dialog = IgnorePatternDialog(
            self, self._ignore_manager
        )

    def _on_scroll(self, *args) -> None:
        """スクロールを同期"""
        self.source_text.yview(*args)
        self.target_text.yview(*args)

    def _open_source_file(self) -> None:
        """ソースファイルを開く"""
        file_path = filedialog.askopenfilename(
            title="ソースファイルを選択",
            filetypes=[
                ("テキストファイル", "*.txt"),
                ("設定ファイル", "*.conf *.cfg"),
                ("全てのファイル", "*.*")
            ]
        )
        if file_path:
            self.source_file_path = file_path
            self.source_label.configure(
                text=f"ソースファイル: {file_path.split('/')[-1]}"
            )
            self.status_bar.configure(
                text=f"ソースファイルを読み込みました: {file_path}"
            )

    def _open_target_file(self) -> None:
        """ターゲットファイルを開く"""
        file_path = filedialog.askopenfilename(
            title="ターゲットファイルを選択",
            filetypes=[
                ("テキストファイル", "*.txt"),
                ("設定ファイル", "*.conf *.cfg"),
                ("全てのファイル", "*.*")
            ]
        )
        if file_path:
            self.target_file_path = file_path
            self.target_label.configure(
                text=f"ターゲットファイル: {file_path.split('/')[-1]}"
            )
            self.status_bar.configure(
                text=f"ターゲットファイルを読み込みました: {file_path}"
            )

    def _on_source_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """source側テキストのクリックハンドラ"""
        row = int(self.source_text.index(f"@{event.x},{event.y}").split(".")[0])
        self._handle_reorder_click(row, side="source")

    def _on_target_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """target側テキストのクリックハンドラ"""
        row = int(self.target_text.index(f"@{event.x},{event.y}").split(".")[0])
        self._handle_reorder_click(row, side="target")

    def _handle_reorder_click(self, row: int, side: str) -> None:
        """reorder行クリック時の処理（ジャンプ＆強調）

        Args:
            row (int): クリックされた行番号（1ベース）
            side (str): クリックされた側 ("source" or "target")
        """
        idx = row - 1  # 0ベースインデックス

        if side == "source":
            if idx >= len(self._src_types) or self._src_types[idx] != "reorder":
                return
            src_key = self._src_keys[idx]
            tgt_row = self._tgt_key_to_row.get(src_key, -1)
            if tgt_row == -1:
                return
            self._apply_active_reorder(row, tgt_row)
            # target側の対応行へスクロール
            self.target_text.see(f"{tgt_row}.0")

        else:  # target
            if idx >= len(self._tgt_types) or self._tgt_types[idx] != "reorder":
                return
            tgt_key = self._tgt_keys[idx]
            src_row = self._src_key_to_row.get(tgt_key, -1)
            if src_row == -1:
                return
            self._apply_active_reorder(src_row, row)
            # source側の対応行へスクロール
            self.source_text.see(f"{src_row}.0")

    def _apply_active_reorder(self, src_row: int, tgt_row: int) -> None:
        """reorder行を強調表示し、前回の強調をリセットする

        Args:
            src_row (int): source側の強調行番号（1ベース）
            tgt_row (int): target側の強調行番号（1ベース）
        """
        # 前回の強調をリセット
        if self._active_src_row != -1:
            self.source_text.tag_remove(
                "reorder_active",
                f"{self._active_src_row}.0",
                f"{self._active_src_row}.end",
            )
        if self._active_tgt_row != -1:
            self.target_text.tag_remove(
                "reorder_active",
                f"{self._active_tgt_row}.0",
                f"{self._active_tgt_row}.end",
            )

        # 新しい強調を適用
        self.source_text.tag_add(
            "reorder_active", f"{src_row}.0", f"{src_row}.end"
        )
        self.target_text.tag_add(
            "reorder_active", f"{tgt_row}.0", f"{tgt_row}.end"
        )
        self._active_src_row = src_row
        self._active_tgt_row = tgt_row

    def _compare_files(self) -> None:
        """ファイルを比較して差分を表示"""
        if not self.source_file_path or not self.target_file_path:
            self.status_bar.configure(
                text="エラー: 両方のファイルを選択してください"
            )
            return

        try:
            # ファイルを読み込み
            with open(self.source_file_path, "r", encoding="utf-8") as f:
                source_content = f.read()

            with open(self.target_file_path, "r", encoding="utf-8") as f:
                target_content = f.read()

            # 選択されたプラットフォームを取得
            platform = _PLATFORM_MAP[self.platform_combobox.get()]

            # 構造的差分に基づいてハイライト情報を計算
            (
                source_lines, target_lines,
                src_types, tgt_types,
                src_keys, tgt_keys,
            ) = (
                TextAlignedDiffComparator
                .compare_and_align_with_structural_diff_info(
                    source_content, target_content, platform
                )
            )

            # 状態を保存
            self._src_types = src_types
            self._tgt_types = tgt_types
            self._src_keys = src_keys
            self._tgt_keys = tgt_keys
            self._active_src_row = -1
            self._active_tgt_row = -1

            # Ignore処理：パターンにマッチした行を差分タイプから除外
            if (
                self._ignore_enabled_var.get()
                and self._ignore_manager.get_patterns()
            ):
                for i, (sl, tl) in enumerate(
                    zip(source_lines, target_lines)
                ):
                    active = sl if sl else tl
                    if active and self._ignore_manager.matches(active):
                        src_types[i] = "ignore"
                        tgt_types[i] = "ignore"

            # reorder行のキー → 行番号マッピングを構築
            self._src_key_to_row = {
                src_keys[i]: i + 1
                for i, t in enumerate(src_types)
                if t == "reorder"
            }
            self._tgt_key_to_row = {
                tgt_keys[i]: i + 1
                for i, t in enumerate(tgt_types)
                if t == "reorder"
            }

            # テキストエリアをクリア
            self.source_text.delete("1.0", "end")
            self.target_text.delete("1.0", "end")

            # 差分を表示
            for i, (src_line, tgt_line, src_type, tgt_type) in enumerate(
                zip(source_lines, target_lines, src_types, tgt_types),
                start=1
            ):
                line_num = f"{i:4d} "

                self.source_text.insert("end", line_num + src_line + "\n")
                self.target_text.insert("end", line_num + tgt_line + "\n")

                # source側タグ適用
                if src_type != "equal":
                    self.source_text.tag_add(
                        src_type, f"{i}.0", f"{i}.end"
                    )

                # target側タグ適用
                if tgt_type != "equal":
                    self.target_text.tag_add(
                        tgt_type, f"{i}.0", f"{i}.end"
                    )

            # 文字単位インライン差分のペアリングと適用
            # delete行（source側のみ）とinsert行（target側のみ）を収集
            delete_rows: list[tuple[int, str]] = []
            insert_rows: list[tuple[int, str]] = []

            for i, (sl, tl, st, tt) in enumerate(
                zip(source_lines, target_lines, src_types, tgt_types), start=1
            ):
                if st == "delete" and tl == "":
                    delete_rows.append((i, sl))
                elif tt == "insert" and sl == "":
                    insert_rows.append((i, tl))
                elif sl != "" and tl != "" and st == "delete" and tt == "insert":
                    # replace オペコード由来：同行に両側コンテンツがある場合
                    ratio = difflib.SequenceMatcher(
                        None, sl, tl, autojunk=False
                    ).ratio()
                    if ratio >= _INLINE_DIFF_THRESHOLD:
                        self._apply_char_diff(i, i, sl, tl)

            # 孤立した delete 行と insert 行を類似度で最良ペアリング
            used_insert: set[int] = set()
            for src_row, src_line in delete_rows:
                best_ratio = 0.0
                best_tgt_row = -1
                best_tgt_line = ""
                for tgt_row, tgt_line in insert_rows:
                    if tgt_row in used_insert:
                        continue
                    ratio = difflib.SequenceMatcher(
                        None, src_line, tgt_line, autojunk=False
                    ).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_tgt_row = tgt_row
                        best_tgt_line = tgt_line
                if best_ratio >= _INLINE_DIFF_THRESHOLD and best_tgt_row != -1:
                    used_insert.add(best_tgt_row)
                    self._apply_char_diff(src_row, best_tgt_row, src_line, best_tgt_line)

            # 統計情報を表示
            delete_count = src_types.count("delete")
            insert_count = tgt_types.count("insert")
            reorder_count = src_types.count("reorder")
            ignore_count = src_types.count("ignore")

            ignore_info = (
                f", Ignore: {ignore_count}行" if ignore_count else ""
            )
            self.status_bar.configure(
                text=f"比較完了 - 削除: {delete_count}行, "
                f"追加: {insert_count}行, "
                f"順番違い: {reorder_count}行"
                f"{ignore_info} "
                f"（順番違いの行はクリックで対応行へジャンプ）"
            )

        except Exception as e:
            self.status_bar.configure(text=f"エラー: {e!s}")


class IgnorePatternDialog(ctk.CTkToplevel):
    """Ignoreパターンを管理するダイアログウィンドウ。

    登録済みパターンの一覧表示・追加・削除を行う。
    設定はOS標準のユーザーデータディレクトリに自動保存される。
    """

    def __init__(
        self,
        parent: ctk.CTk,
        manager: IgnorePatternManager,
    ) -> None:
        super().__init__(parent)
        self._manager = manager
        self.title("Ignoreパターン管理")
        self.geometry("560x440")
        self.resizable(True, True)
        self.transient(parent)
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
                command=lambda p=pattern: self._remove_pattern(p),
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
            self._error_label.configure(
                text=f"正規表現エラー: {e}"
            )
        except ValueError as e:
            self._error_label.configure(text=str(e))

    def _remove_pattern(self, pattern: str) -> None:
        """指定パターンを削除する。

        Args:
            pattern: 削除するパターン文字列
        """
        self._manager.remove_pattern(pattern)
        self._refresh_list()


def main() -> None:
    """アプリケーションのエントリーポイント"""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = DiffViewerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
