"""比較機能のビューモジュール。

2つのネットワーク機器コンフィグファイルを比較し、差分を視覚的に表示する
UIコンポーネントを提供する。
"""

import difflib
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from src.compare.ignore import IgnorePatternDialog, IgnorePatternManager
from src.compare.logic import TextAlignedDiffComparator
from src.compare.platforms import PLATFORM_MAP
from src.compare.settings import AppSettings

# 文字単位インライン差分の設定
_INLINE_DIFF_THRESHOLD: float = 0.4  # ペアリングに必要な最低類似度
_LINE_NUM_WIDTH: int = 5  # 行番号プレフィックスの文字数 ("   1 ")

# Platform 選択肢マッピング（platforms.py から共通インポート）
_PLATFORM_MAP = PLATFORM_MAP


class CompareView(ctk.CTkFrame):
    """コンフィグファイルの差分を2列で比較表示するビュー。

    ツールバー（ファイル選択・Platformセレクタ・Compareボタン・
    Ignoreパターン管理）とテキストエリアで構成される。
    """

    def __init__(
        self,
        parent: ctk.CTk | ctk.CTkBaseClass,
        settings: AppSettings,
    ) -> None:
        super().__init__(parent, corner_radius=0, fg_color="transparent")

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

        # 現在アクティブな reorder 強調表示の行番号（1ベース）
        self._active_src_row: int = -1
        self._active_tgt_row: int = -1

        # Ignore機能
        self._ignore_manager: IgnorePatternManager = IgnorePatternManager(
            settings
        )
        self._ignore_enabled_var: tk.BooleanVar = tk.BooleanVar(value=True)
        self._ignore_dialog: "IgnorePatternDialog | None" = None

        # 比較済みフラグ（Ignoreトグル時の自動再比較に使用）
        self._has_compared: bool = False

        # 左右スクロール同期の再入防止フラグ
        self._syncing_scroll: bool = False

        # UIの構築
        self._create_widgets()

        # Ignoreトグル変更時に自動再比較
        self._ignore_enabled_var.trace_add("write", self._on_ignore_toggle)

    # ------------------------------------------------------------------
    # UI構築
    # ------------------------------------------------------------------

    def _create_widgets(self) -> None:
        """UIウィジェットを作成する。"""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- ツールバー ---
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        toolbar.grid_columnconfigure(0, weight=1)
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.grid_columnconfigure(2, weight=0)
        toolbar.grid_columnconfigure(3, weight=0)
        toolbar.grid_columnconfigure(4, weight=0)

        # ソースファイル選択
        src_file_frame = ctk.CTkFrame(toolbar)
        src_file_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        src_file_frame.grid_columnconfigure(0, weight=1)

        self.source_label = ctk.CTkLabel(
            src_file_frame,
            text="Source File: Not Selected",
            anchor="w",
        )
        self.source_label.grid(row=0, column=0, padx=5, sticky="ew")

        ctk.CTkButton(
            src_file_frame,
            text="Open",
            command=self._open_source_file,
            width=70,
        ).grid(row=0, column=1, padx=5, pady=4)

        # ターゲットファイル選択
        tgt_file_frame = ctk.CTkFrame(toolbar)
        tgt_file_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        tgt_file_frame.grid_columnconfigure(0, weight=1)

        self.target_label = ctk.CTkLabel(
            tgt_file_frame,
            text="Target File: Not Selected",
            anchor="w",
        )
        self.target_label.grid(row=0, column=0, padx=5, sticky="ew")

        ctk.CTkButton(
            tgt_file_frame,
            text="Open",
            command=self._open_target_file,
            width=70,
        ).grid(row=0, column=1, padx=5, pady=4)

        # Platformセレクタ
        platform_frame = ctk.CTkFrame(toolbar)
        platform_frame.grid(row=0, column=2, padx=5, pady=5)
        platform_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            platform_frame, text="Platform:"
        ).grid(row=0, column=0, padx=(6, 2), pady=6)

        self.platform_combobox = ctk.CTkComboBox(
            platform_frame,
            values=list(_PLATFORM_MAP.keys()),
            width=160,
            state="readonly",
        )
        self.platform_combobox.set("CISCO_IOS")
        self.platform_combobox.grid(row=0, column=1, padx=(0, 6), pady=6)

        # 比較ボタン
        ctk.CTkButton(
            toolbar,
            text="Compare",
            command=self._compare_files,
            width=100,
            fg_color="green",
            hover_color="darkgreen",
        ).grid(row=0, column=3, padx=10, pady=5)

        # Ignoreパターン管理 + トグルスイッチ
        ignore_frame = ctk.CTkFrame(toolbar)
        ignore_frame.grid(row=0, column=4, padx=5, pady=5)
        ignore_frame.grid_columnconfigure(0, weight=0)
        ignore_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkButton(
            ignore_frame,
            text="Manage Ignore Patterns",
            command=self._open_ignore_dialog,
            width=160,
        ).grid(row=0, column=0, padx=(5, 8), pady=6)

        self._ignore_switch = ctk.CTkSwitch(
            ignore_frame,
            text="Enable Ignore",
            variable=self._ignore_enabled_var,
            onvalue=True,
            offvalue=False,
        )
        self._ignore_switch.grid(row=0, column=1, padx=(0, 8), pady=6)

        # --- メインフレーム（テキスト表示エリア）---
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(
            row=1, column=0, sticky="nsew", padx=10, pady=(0, 10)
        )
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # ヘッダー行
        ctk.CTkLabel(
            main_frame,
            text="Source",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, pady=5)

        ctk.CTkLabel(
            main_frame,
            text="Target",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=1, pady=5)

        # 左テキストエリア（ソース）
        left_text_frame = ctk.CTkFrame(main_frame)
        left_text_frame.grid(
            row=1, column=0, sticky="nsew", padx=(5, 2), pady=(0, 5)
        )
        left_text_frame.grid_rowconfigure(0, weight=1)
        left_text_frame.grid_columnconfigure(0, weight=1)

        self.source_text = tk.Text(
            left_text_frame,
            wrap="none",
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="#ffffff",
            font=("Courier", 11),
            cursor="arrow",
        )
        self.source_text.grid(row=0, column=0, sticky="nsew")
        self.source_text.bind("<Button-1>", self._on_source_click)
        self.source_text.bind("<MouseWheel>", self._on_mousewheel)
        self.source_text.bind("<Button-4>", self._on_mousewheel_linux)
        self.source_text.bind("<Button-5>", self._on_mousewheel_linux)

        self.source_scrollbar = ctk.CTkScrollbar(
            left_text_frame, command=self._on_scroll
        )
        self.source_scrollbar.grid(row=0, column=1, sticky="ns")
        self.source_text.config(yscrollcommand=self._on_source_yscroll)

        # 右テキストエリア（ターゲット）
        right_text_frame = ctk.CTkFrame(main_frame)
        right_text_frame.grid(
            row=1, column=1, sticky="nsew", padx=(2, 5), pady=(0, 5)
        )
        right_text_frame.grid_rowconfigure(0, weight=1)
        right_text_frame.grid_columnconfigure(0, weight=1)

        self.target_text = tk.Text(
            right_text_frame,
            wrap="none",
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="#ffffff",
            font=("Courier", 11),
            cursor="arrow",
        )
        self.target_text.grid(row=0, column=0, sticky="nsew")
        self.target_text.bind("<Button-1>", self._on_target_click)
        self.target_text.bind("<MouseWheel>", self._on_mousewheel)
        self.target_text.bind("<Button-4>", self._on_mousewheel_linux)
        self.target_text.bind("<Button-5>", self._on_mousewheel_linux)

        self.target_scrollbar = ctk.CTkScrollbar(
            right_text_frame, command=self._on_scroll
        )
        self.target_scrollbar.grid(row=0, column=1, sticky="ns")
        self.target_text.config(yscrollcommand=self._on_target_yscroll)

        # タグの設定（差分の色分け）
        self._configure_tags()

        # ステータスバー
        self.status_bar = ctk.CTkLabel(
            self,
            text="ファイルを選択して比較を開始してください",
            anchor="w",
        )
        self.status_bar.grid(
            row=2, column=0, sticky="ew", padx=10, pady=(0, 5)
        )

    def _configure_tags(self) -> None:
        """テキストウィジェットのタグを設定する。"""
        # 削除された行（sourceのみに存在）
        self.source_text.tag_configure(
            "delete",
            background="#4d1f1f",
            foreground="#ff6b6b",
        )

        # 挿入された行（targetのみに存在）
        self.target_text.tag_configure(
            "insert",
            background="#1f4d1f",
            foreground="#6bff6b",
        )

        # 順番違い（両方に存在するが順番が異なる）
        for widget in (self.source_text, self.target_text):
            widget.tag_configure(
                "reorder",
                background="#4d3b1f",
                foreground="#ffb347",
            )
            # クリック時の強調表示
            widget.tag_configure(
                "reorder_active",
                background="#7a5a1a",
                foreground="#ffe680",
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

    # ------------------------------------------------------------------
    # イベントハンドラ
    # ------------------------------------------------------------------

    def _on_ignore_toggle(self, *_: object) -> None:
        """Ignoreスイッチ切り替え時に比較済みなら自動で再比較する。"""
        if self._has_compared:
            self._compare_files()

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
        self._ignore_dialog = IgnorePatternDialog(self, self._ignore_manager)

    def _on_source_yscroll(self, first: float, last: float) -> None:
        """source テキストがスクロールされたとき scrollbar を更新し target を同期する。"""
        self.source_scrollbar.set(first, last)
        if not self._syncing_scroll:
            self._syncing_scroll = True
            self.target_text.yview_moveto(first)
            self._syncing_scroll = False

    def _on_target_yscroll(self, first: float, last: float) -> None:
        """target テキストがスクロールされたとき scrollbar を更新し source を同期する。"""
        self.target_scrollbar.set(first, last)
        if not self._syncing_scroll:
            self._syncing_scroll = True
            self.source_text.yview_moveto(first)
            self._syncing_scroll = False

    def _on_scroll(self, *args: object) -> None:
        """スクロールバーのドラッグで左右テキストを同期スクロールする。"""
        self.source_text.yview(*args)
        self.target_text.yview(*args)

    def _on_mousewheel(self, event: tk.Event) -> str:  # type: ignore[type-arg]
        """マウスホイール操作で両テキストを同期スクロールする（Windows / macOS）。

        Args:
            event: マウスホイールイベント。

        Returns:
            "break" でデフォルトのスクロール動作を抑止する。
        """
        scroll_units = int(-1 * (event.delta / 120))
        if scroll_units == 0:
            scroll_units = -1 if event.delta > 0 else 1
        widget = event.widget
        if isinstance(widget, tk.Text):
            widget.yview_scroll(scroll_units, "units")
        return "break"

    def _on_mousewheel_linux(self, event: tk.Event) -> str:  # type: ignore[type-arg]
        """マウスホイール操作で両テキストを同期スクロールする（Linux）。

        Args:
            event: Button-4 / Button-5 イベント。

        Returns:
            "break" でデフォルトのスクロール動作を抑止する。
        """
        widget = event.widget
        if not isinstance(widget, tk.Text):
            return "break"
        if event.num == 4:
            widget.yview_scroll(-1, "units")
        elif event.num == 5:
            widget.yview_scroll(1, "units")
        return "break"

    def _open_source_file(self) -> None:
        """ソースファイルを開く。"""
        file_path = filedialog.askopenfilename(
            title="ソースファイルを選択",
            filetypes=[
                ("テキストファイル", "*.txt"),
                ("設定ファイル", "*.conf *.cfg"),
                ("全てのファイル", "*.*"),
            ],
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
        """ターゲットファイルを開く。"""
        file_path = filedialog.askopenfilename(
            title="ターゲットファイルを選択",
            filetypes=[
                ("テキストファイル", "*.txt"),
                ("設定ファイル", "*.conf *.cfg"),
                ("全てのファイル", "*.*"),
            ],
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
        """source側テキストのクリックハンドラ。"""
        row = int(
            self.source_text.index(f"@{event.x},{event.y}").split(".")[0]
        )
        self._handle_reorder_click(row, side="source")

    def _on_target_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """target側テキストのクリックハンドラ。"""
        row = int(
            self.target_text.index(f"@{event.x},{event.y}").split(".")[0]
        )
        self._handle_reorder_click(row, side="target")

    def _handle_reorder_click(self, row: int, side: str) -> None:
        """reorder行クリック時の処理（ジャンプ＆強調）。

        Args:
            row: クリックされた行番号（1ベース）
            side: クリックされた側（``"source"`` または ``"target"``）
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
            self.target_text.see(f"{tgt_row}.0")

        else:  # target
            if idx >= len(self._tgt_types) or self._tgt_types[idx] != "reorder":
                return
            tgt_key = self._tgt_keys[idx]
            src_row = self._src_key_to_row.get(tgt_key, -1)
            if src_row == -1:
                return
            self._apply_active_reorder(src_row, row)
            self.source_text.see(f"{src_row}.0")

    def _apply_active_reorder(self, src_row: int, tgt_row: int) -> None:
        """reorder行を強調表示し、前回の強調をリセットする。

        Args:
            src_row: source側の強調行番号（1ベース）
            tgt_row: target側の強調行番号（1ベース）
        """
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

        self.source_text.tag_add(
            "reorder_active", f"{src_row}.0", f"{src_row}.end"
        )
        self.target_text.tag_add(
            "reorder_active", f"{tgt_row}.0", f"{tgt_row}.end"
        )
        self._active_src_row = src_row
        self._active_tgt_row = tgt_row

    def _apply_char_diff(
        self,
        src_row: int,
        tgt_row: int,
        src_line: str,
        tgt_line: str,
    ) -> None:
        """2行間の文字単位差分を強調表示する。

        Args:
            src_row: source側の行番号（1ベース）
            tgt_row: target側の行番号（1ベース）
            src_line: source側の行テキスト（行番号プレフィックスなし）
            tgt_line: target側の行テキスト（行番号プレフィックスなし）
        """
        matcher = difflib.SequenceMatcher(
            None, src_line, tgt_line, autojunk=False
        )
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

    # ------------------------------------------------------------------
    # 比較処理
    # ------------------------------------------------------------------

    def _compare_files(self) -> None:
        """ファイルを比較して差分を表示する。"""
        if not self.source_file_path or not self.target_file_path:
            self.status_bar.configure(
                text="エラー: 両方のファイルを選択してください"
            )
            return

        try:
            with open(self.source_file_path, encoding="utf-8") as f:
                source_content = f.read()

            with open(self.target_file_path, encoding="utf-8") as f:
                target_content = f.read()

            platform = _PLATFORM_MAP[self.platform_combobox.get()]

            (
                source_lines,
                target_lines,
                src_types,
                tgt_types,
                src_keys,
                tgt_keys,
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
                start=1,
            ):
                line_num = f"{i:4d} "

                self.source_text.insert("end", line_num + src_line + "\n")
                self.target_text.insert("end", line_num + tgt_line + "\n")

                if src_type != "equal":
                    self.source_text.tag_add(
                        src_type, f"{i}.0", f"{i}.end"
                    )
                if tgt_type != "equal":
                    self.target_text.tag_add(
                        tgt_type, f"{i}.0", f"{i}.end"
                    )

            # 文字単位インライン差分のペアリングと適用
            delete_rows: list[tuple[int, str]] = []
            insert_rows: list[tuple[int, str]] = []

            for i, (sl, tl, st, tt) in enumerate(
                zip(source_lines, target_lines, src_types, tgt_types),
                start=1,
            ):
                if st == "delete" and tl == "":
                    delete_rows.append((i, sl))
                elif tt == "insert" and sl == "":
                    insert_rows.append((i, tl))
                elif sl != "" and tl != "" and st == "delete" and tt == "insert":
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
                    self._apply_char_diff(
                        src_row, best_tgt_row, src_line, best_tgt_line
                    )

            # 統計情報を表示
            delete_count = src_types.count("delete")
            insert_count = tgt_types.count("insert")
            reorder_count = src_types.count("reorder")
            ignore_count = src_types.count("ignore")

            ignore_info = (
                f", Ignore: {ignore_count}行" if ignore_count else ""
            )
            self.status_bar.configure(
                text=(
                    f"比較完了 - 削除: {delete_count}行, "
                    f"追加: {insert_count}行, "
                    f"順番違い: {reorder_count}行"
                    f"{ignore_info} "
                    f"（順番違いの行はクリックで対応行へジャンプ）"
                )
            )
            self._has_compared = True

        except Exception as e:
            self.status_bar.configure(text=f"エラー: {e!s}")
