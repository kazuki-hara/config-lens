"""比較結果ウィンドウモジュール。

File Compare / Folder Compare の両方から呼び出される差分表示専用の
Toplevel ウィンドウを提供する。
"""

import difflib
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from src.compare.ignore import IgnorePatternDialog, IgnorePatternManager
from src.compare.logic import TextAlignedDiffComparator
from src.compare.normalizer import VLAN_DIFF_ANNOTATION_MARKER
from src.compare.platforms import PLATFORM_MAP
from src.compare.settings import AppSettings

# 文字単位インライン差分の設定
_INLINE_DIFF_THRESHOLD: float = 0.4
_LINE_NUM_WIDTH: int = 5
_SCROLL_SPEED: int = 3

_PLATFORM_MAP = PLATFORM_MAP


class CompareResultWindow(ctk.CTkToplevel):
    """2つのファイルの差分を表示する Toplevel ウィンドウ。

    File Compare・Folder Compare のどちらからも起動できる。
    ナビゲーションバー・テキストエリア・Ignore トグルを持ち、
    ウィンドウを開いた直後に比較を自動実行する。
    """

    def __init__(
        self,
        parent: ctk.CTk | ctk.CTkBaseClass,
        src_path: Path,
        tgt_path: Path,
        platform_name: str,
        settings: AppSettings,
    ) -> None:
        """初期化。

        Args:
            parent: 親ウィジェット
            src_path: ソースファイルのパス
            tgt_path: ターゲットファイルのパス
            platform_name: プラットフォーム名（PLATFORM_MAP のキー）
            settings: アプリ共有設定
        """
        super().__init__(parent)

        self.title(f"Compare: {src_path.name}  ↔  {tgt_path.name}")
        self.geometry("1400x800")

        self._src_path = src_path
        self._tgt_path = tgt_path
        self._platform_name = platform_name

        # 比較結果のキー情報（クリックジャンプ用）
        self._src_key_to_row: dict[str, int] = {}
        self._tgt_key_to_row: dict[str, int] = {}
        self._src_types: list[str] = []
        self._tgt_types: list[str] = []
        self._src_keys: list[str] = []
        self._tgt_keys: list[str] = []

        self._active_src_row: int = -1
        self._active_tgt_row: int = -1

        self._highlighted_rows: list[int] = []
        self._nav_index: int = -1
        self._nav_current_row: int = -1

        self._ignore_manager = IgnorePatternManager(settings)
        self._ignore_enabled_var = tk.BooleanVar(value=True)
        self._ignore_dialog: "IgnorePatternDialog | None" = None

        self._syncing_scroll: bool = False

        self._create_widgets()
        self._ignore_enabled_var.trace_add("write", self._on_ignore_toggle)

        # ウィンドウ表示後に比較を実行
        self.after(100, self._compare_files)

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _create_widgets(self) -> None:
        """UIウィジェットを作成する。"""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- ナビゲーションバー ---
        nav_bar = ctk.CTkFrame(self)
        nav_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))

        self._prev_btn = ctk.CTkButton(
            nav_bar,
            text="◀ Prev",
            command=self._nav_prev,
            width=80,
            state="disabled",
        )
        self._prev_btn.pack(side="left", padx=(5, 2), pady=4)

        self._nav_counter_label = ctk.CTkLabel(
            nav_bar, text="- / -", width=100, anchor="center"
        )
        self._nav_counter_label.pack(side="left", padx=8)

        self._next_btn = ctk.CTkButton(
            nav_bar,
            text="Next ▶",
            command=self._nav_next,
            width=80,
            state="disabled",
        )
        self._next_btn.pack(side="left", padx=(2, 5), pady=4)

        # Ignore トグル
        ignore_frame = ctk.CTkFrame(nav_bar)
        ignore_frame.pack(side="right", padx=5, pady=4)

        ctk.CTkButton(
            ignore_frame,
            text="Manage Ignore Patterns",
            command=self._open_ignore_dialog,
            width=160,
        ).pack(side="left", padx=(5, 8), pady=4)

        self._ignore_switch = ctk.CTkSwitch(
            ignore_frame,
            text="Enable Ignore",
            variable=self._ignore_enabled_var,
            onvalue=True,
            offvalue=False,
        )
        self._ignore_switch.pack(side="left", padx=(0, 8), pady=4)

        # --- メインフレーム（テキスト表示エリア）---
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(
            row=1, column=0, sticky="nsew", padx=10, pady=(0, 4)
        )
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # ヘッダー行
        ctk.CTkLabel(
            main_frame,
            text=f"Source: {self._src_path.name}",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(
            main_frame,
            text=f"Target: {self._tgt_path.name}",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

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
            state="disabled",
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
            state="disabled",
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

        self._configure_tags()

        # ステータスバー
        self.status_bar = ctk.CTkLabel(
            self,
            text="比較中...",
            anchor="w",
        )
        self.status_bar.grid(
            row=2, column=0, sticky="ew", padx=10, pady=(0, 5)
        )

    def _configure_tags(self) -> None:
        """テキストウィジェットのタグを設定する。"""
        self.source_text.tag_configure(
            "delete",
            background="#5a1e1e",
            foreground="#ffaaaa",
        )
        self.target_text.tag_configure(
            "insert",
            background="#1e5a24",
            foreground="#aaffaa",
        )
        for widget in (self.source_text, self.target_text):
            widget.tag_configure(
                "reorder",
                background="#4d4020",
                foreground="#ffd966",
            )
            widget.tag_configure(
                "reorder_active",
                background="#7a6620",
                foreground="#fff0a0",
            )
        self.source_text.tag_configure("empty", background="#1a1a1a")
        self.target_text.tag_configure("empty", background="#1a1a1a")
        for widget in (self.source_text, self.target_text):
            widget.tag_configure(
                "vlan_annotation",
                background="#2a2a2a",
                foreground="#888888",
            )
        self.source_text.tag_configure(
            "delete_char", background="#cc2200", foreground="#ffe8e8"
        )
        self.target_text.tag_configure(
            "insert_char", background="#00aa44", foreground="#e8ffe8"
        )
        for widget in (self.source_text, self.target_text):
            widget.tag_configure(
                "ignore",
                background="#2f2f2f",
                foreground="#5a5a5a",
            )
            widget.tag_configure(
                "nav_current",
                background="#1a52a0",
                foreground="#ffffff",
            )
        for widget in (self.source_text, self.target_text):
            widget.tag_raise("nav_current")
            widget.tag_raise("reorder_active")
        self.source_text.tag_raise("delete_char")
        self.target_text.tag_raise("insert_char")

    # ------------------------------------------------------------------
    # イベントハンドラ
    # ------------------------------------------------------------------

    def _on_ignore_toggle(self, *_: object) -> None:
        """Ignore スイッチ切り替え時に自動再比較する。"""
        self._compare_files()

    def _open_ignore_dialog(self) -> None:
        """Ignore パターン管理ダイアログを開く。"""
        if (
            self._ignore_dialog is not None
            and self._ignore_dialog.winfo_exists()
        ):
            self._ignore_dialog.lift()
            return
        self._ignore_dialog = IgnorePatternDialog(self, self._ignore_manager)  # type: ignore[arg-type]

    def _on_source_yscroll(self, first: float, last: float) -> None:
        """source テキストスクロール時に scrollbar と target を同期する。"""
        self.source_scrollbar.set(first, last)
        if not self._syncing_scroll:
            self._syncing_scroll = True
            self.target_text.yview_moveto(first)
            self._syncing_scroll = False

    def _on_target_yscroll(self, first: float, last: float) -> None:
        """target テキストスクロール時に scrollbar と source を同期する。"""
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
        """マウスホイール操作で両テキストを同期スクロールする（Windows/macOS）。

        Args:
            event: マウスホイールイベント。

        Returns:
            "break" でデフォルトのスクロール動作を抑止する。
        """
        scroll_units = int(-1 * (event.delta / 120)) * _SCROLL_SPEED
        if scroll_units == 0:
            scroll_units = (
                -_SCROLL_SPEED if event.delta > 0 else _SCROLL_SPEED
            )
        widget = event.widget
        if isinstance(widget, tk.Text):
            widget.yview_scroll(scroll_units, "units")
        return "break"

    def _on_mousewheel_linux(
        self, event: tk.Event  # type: ignore[type-arg]
    ) -> str:
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
            widget.yview_scroll(-_SCROLL_SPEED, "units")
        elif event.num == 5:
            widget.yview_scroll(_SCROLL_SPEED, "units")
        return "break"

    def _on_source_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """source 側テキストのクリックハンドラ。"""
        row = int(
            self.source_text.index(f"@{event.x},{event.y}").split(".")[0]
        )
        self._handle_reorder_click(row, side="source")

    def _on_target_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """target 側テキストのクリックハンドラ。"""
        row = int(
            self.target_text.index(f"@{event.x},{event.y}").split(".")[0]
        )
        self._handle_reorder_click(row, side="target")

    def _handle_reorder_click(self, row: int, side: str) -> None:
        """reorder 行クリック時の処理（ジャンプ＆強調）。

        Args:
            row: クリックされた行番号（1 ベース）
            side: クリックされた側（``"source"`` または ``"target"``）
        """
        idx = row - 1
        if side == "source":
            if (
                idx >= len(self._src_types)
                or self._src_types[idx] != "reorder"
            ):
                return
            src_key = self._src_keys[idx]
            tgt_row = self._tgt_key_to_row.get(src_key, -1)
            if tgt_row == -1:
                return
            self._apply_active_reorder(row, tgt_row)
            self.target_text.see(f"{tgt_row}.0")
        else:
            if (
                idx >= len(self._tgt_types)
                or self._tgt_types[idx] != "reorder"
            ):
                return
            tgt_key = self._tgt_keys[idx]
            src_row = self._src_key_to_row.get(tgt_key, -1)
            if src_row == -1:
                return
            self._apply_active_reorder(src_row, row)
            self.source_text.see(f"{src_row}.0")

    def _apply_active_reorder(self, src_row: int, tgt_row: int) -> None:
        """reorder 行を強調表示し、前回の強調をリセットする。

        Args:
            src_row: source 側の強調行番号（1 ベース）
            tgt_row: target 側の強調行番号（1 ベース）
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

    # ------------------------------------------------------------------
    # ナビゲーション
    # ------------------------------------------------------------------

    def _nav_next(self) -> None:
        """次のハイライト行へジャンプする。"""
        if not self._highlighted_rows:
            return
        self._nav_index = min(
            self._nav_index + 1, len(self._highlighted_rows) - 1
        )
        self._jump_to_nav_row()

    def _nav_prev(self) -> None:
        """前のハイライト行へジャンプする。"""
        if not self._highlighted_rows:
            return
        self._nav_index = max(self._nav_index - 1, 0)
        self._jump_to_nav_row()

    def _jump_to_nav_row(self) -> None:
        """現在のナビゲーションインデックスの行へ両テキストをスクロールする。"""
        if not self._highlighted_rows or self._nav_index < 0:
            return
        row = self._highlighted_rows[self._nav_index]
        if self._nav_current_row != -1:
            for widget in (self.source_text, self.target_text):
                widget.tag_remove(
                    "nav_current",
                    f"{self._nav_current_row}.0",
                    f"{self._nav_current_row}.end",
                )
        for widget in (self.source_text, self.target_text):
            widget.tag_add("nav_current", f"{row}.0", f"{row}.end")
        self._nav_current_row = row
        self.source_text.see(f"{row}.0")
        self._update_nav_counter()

    def _update_nav_counter(self) -> None:
        """ナビゲーションカウンターラベルを更新する。"""
        total = len(self._highlighted_rows)
        if total == 0:
            self._nav_counter_label.configure(text="差分なし")
        else:
            current = self._nav_index + 1 if self._nav_index >= 0 else 0
            self._nav_counter_label.configure(
                text=f"{current} / {total} 差分"
            )

    # ------------------------------------------------------------------
    # 文字単位差分
    # ------------------------------------------------------------------

    def _apply_char_diff(
        self,
        src_row: int,
        tgt_row: int,
        src_line: str,
        tgt_line: str,
    ) -> None:
        """2 行間の文字単位差分を強調表示する。

        Args:
            src_row: source 側の行番号（1 ベース）
            tgt_row: target 側の行番号（1 ベース）
            src_line: source 側の行テキスト（行番号プレフィックスなし）
            tgt_line: target 側の行テキスト（行番号プレフィックスなし）
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
        try:
            src_text = self._src_path.read_text(encoding="utf-8")
            tgt_text = self._tgt_path.read_text(encoding="utf-8")

            platform = _PLATFORM_MAP[self._platform_name]

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
                    src_text, tgt_text, platform, normalize=True
                )
            )

            self._src_types = src_types
            self._tgt_types = tgt_types
            self._src_keys = src_keys
            self._tgt_keys = tgt_keys
            self._active_src_row = -1
            self._active_tgt_row = -1

            # Ignore 処理
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

            # reorder 行のキー → 行番号マッピング
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

            # テキスト描画
            self.source_text.config(state="normal")
            self.target_text.config(state="normal")
            self.source_text.delete("1.0", "end")
            self.target_text.delete("1.0", "end")

            for i, (src_line, tgt_line, src_type, tgt_type) in enumerate(
                zip(source_lines, target_lines, src_types, tgt_types),
                start=1,
            ):
                line_num = f"{i:4d} "
                self.source_text.insert("end", line_num + src_line + "\n")
                self.target_text.insert("end", line_num + tgt_line + "\n")
                # VLANアノテーション行はグレーで上書き表示
                active_line = src_line if src_line else tgt_line
                if VLAN_DIFF_ANNOTATION_MARKER in active_line:
                    self.source_text.tag_add(
                        "vlan_annotation", f"{i}.0", f"{i}.end"
                    )
                    self.target_text.tag_add(
                        "vlan_annotation", f"{i}.0", f"{i}.end"
                    )
                    continue
                if src_type != "equal":
                    self.source_text.tag_add(
                        src_type, f"{i}.0", f"{i}.end"
                    )
                if tgt_type != "equal":
                    self.target_text.tag_add(
                        tgt_type, f"{i}.0", f"{i}.end"
                    )

            self.source_text.config(state="disabled")
            self.target_text.config(state="disabled")

            # 文字単位インライン差分
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
                elif sl and tl and st == "delete" and tt == "insert":
                    ratio = difflib.SequenceMatcher(
                        None, sl, tl, autojunk=False
                    ).ratio()
                    if ratio >= _INLINE_DIFF_THRESHOLD:
                        self._apply_char_diff(i, i, sl, tl)

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

            # 統計
            delete_count = src_types.count("delete")
            insert_count = tgt_types.count("insert")
            reorder_count = src_types.count("reorder")
            ignore_count = src_types.count("ignore")
            ignore_info = (
                f", Ignore: {ignore_count} 行" if ignore_count else ""
            )
            self.status_bar.configure(
                text=(
                    f"比較完了 - 削除: {delete_count} 行, "
                    f"追加: {insert_count} 行, "
                    f"順番違い: {reorder_count} 行"
                    f"{ignore_info} "
                    f"（順番違いの行はクリックで対応行へジャンプ）"
                )
            )

            # ナビゲーション構築
            highlighted: set[int] = set()
            for i, (st, tt, sl, tl) in enumerate(
                zip(src_types, tgt_types, source_lines, target_lines), start=1
            ):
                active = sl if sl else tl
                if VLAN_DIFF_ANNOTATION_MARKER in active:
                    continue  # アノテーション行はナビゲーション対象外
                if st in ("delete", "insert", "reorder") or tt in (
                    "delete",
                    "insert",
                    "reorder",
                ):
                    highlighted.add(i)
            self._highlighted_rows = sorted(highlighted)
            self._nav_index = -1
            self._nav_current_row = -1
            if self._highlighted_rows:
                self._prev_btn.configure(state="normal")
                self._next_btn.configure(state="normal")
            else:
                self._prev_btn.configure(state="disabled")
                self._next_btn.configure(state="disabled")
            self._update_nav_counter()

        except Exception as e:
            self.status_bar.configure(text=f"エラー: {e!s}")
