"""Config Validator のビューモジュール。

現在のrunning-config・設定変更内容・想定されるrunning-configの
3ファイルを入力として受け取り、running ↔ expected の差分が
設定変更内容に起因するかどうかを構造的差分解析で視覚的に検証する。

列構成（左→右）:
    - 現在のrunning-config  : 削除差分を赤/黄色でハイライト
    - 設定変更内容          : 差分に対応する行を黄色でハイライト、クリックで連動
    - 想定されるrunning-config : 追加差分を緑/黄色でハイライト
"""

import difflib
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk
from hier_config import Platform

from src.validate.logic import ValidateResult, validate

# Platform 選択肢（CompareView と同じマッピング）
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

# 文字単位インライン差分の最低類似度
_INLINE_DIFF_THRESHOLD: float = 0.4
# 行番号プレフィックスの文字幅 ("   1 " = 5文字)
_LINE_NUM_WIDTH: int = 5


class ValidateView(ctk.CTkFrame):
    """3列で実行する Config Validator ビュー。

    running ↔ expected の構造的差分を計算し、

    - 設定変更内容由来の差分 → 黄色（change_remove / change_add）
    - 由来不明の差分 → 赤（remove）/ 緑（add）

    でハイライトする。設定変更内容の黄色行をクリックすると、
    対応する running / expected 行を濃い黄色でハイライトし、
    スクロールで表示する。
    """

    def __init__(
        self,
        parent: ctk.CTk | ctk.CTkBaseClass,
    ) -> None:
        """初期化。

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent, corner_radius=0, fg_color="transparent")

        # ファイルパス
        self._running_path: str = ""
        self._change_path: str = ""
        self._expected_path: str = ""

        # 検証結果
        self._result: ValidateResult | None = None

        # 現在アクティブな change 行インデックス（0ベース、-1 = 選択なし）
        self._active_change_idx: int = -1
        # アクティブハイライト中の running / expected 行番号（1ベース）
        self._active_running_rows: list[int] = []
        self._active_expected_rows: list[int] = []

        self._create_widgets()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _create_widgets(self) -> None:
        """全ウィジェットを構築する。"""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_toolbar()
        self._create_main_area()
        self._create_status_bar()

    def _create_toolbar(self) -> None:
        """ツールバー（ファイル選択×3・Platform・Validateボタン）を構築する。"""
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        toolbar.grid_columnconfigure(0, weight=1)
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.grid_columnconfigure(2, weight=1)
        toolbar.grid_columnconfigure(3, weight=0)
        toolbar.grid_columnconfigure(4, weight=0)

        # Running Config ファイル選択
        running_frame = ctk.CTkFrame(toolbar)
        running_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        running_frame.grid_columnconfigure(0, weight=1)

        self._running_label = ctk.CTkLabel(
            running_frame,
            text="Running Config: 未選択",
            anchor="w",
        )
        self._running_label.grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(
            running_frame,
            text="Open",
            command=self._open_running_config,
            width=70,
        ).grid(row=0, column=1, padx=5, pady=4)

        # Change Config ファイル選択
        change_frame = ctk.CTkFrame(toolbar)
        change_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        change_frame.grid_columnconfigure(0, weight=1)

        self._change_label = ctk.CTkLabel(
            change_frame,
            text="Change Config: 未選択",
            anchor="w",
        )
        self._change_label.grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(
            change_frame,
            text="Open",
            command=self._open_change_config,
            width=70,
        ).grid(row=0, column=1, padx=5, pady=4)

        # Expected Config ファイル選択
        expected_frame = ctk.CTkFrame(toolbar)
        expected_frame.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
        expected_frame.grid_columnconfigure(0, weight=1)

        self._expected_label = ctk.CTkLabel(
            expected_frame,
            text="Expected Config: 未選択",
            anchor="w",
        )
        self._expected_label.grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(
            expected_frame,
            text="Open",
            command=self._open_expected_config,
            width=70,
        ).grid(row=0, column=1, padx=5, pady=4)

        # Platform セレクタ
        platform_frame = ctk.CTkFrame(toolbar)
        platform_frame.grid(row=0, column=3, padx=5, pady=5)
        ctk.CTkLabel(platform_frame, text="Platform:").grid(
            row=0, column=0, padx=(6, 2), pady=6
        )
        self._platform_combobox = ctk.CTkComboBox(
            platform_frame,
            values=list(_PLATFORM_MAP.keys()),
            width=160,
            state="readonly",
        )
        self._platform_combobox.set("CISCO_IOS")
        self._platform_combobox.grid(row=0, column=1, padx=(0, 6), pady=6)

        # Validate ボタン
        ctk.CTkButton(
            toolbar,
            text="Validate",
            command=self._on_validate,
            width=100,
            fg_color="green",
            hover_color="darkgreen",
        ).grid(row=0, column=4, padx=10, pady=5)

    def _create_main_area(self) -> None:
        """3列のテキストエリアを構築する。"""
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(
            row=1, column=0, sticky="nsew", padx=10, pady=(0, 10)
        )
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)

        # ヘッダー
        for col, title in enumerate([
            "現在のrunning-config",
            "設定変更内容",
            "想定されるrunning-config",
        ]):
            ctk.CTkLabel(
                main_frame,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=col, pady=5)

        # 左: running
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.grid(
            row=1, column=0, sticky="nsew", padx=(5, 2), pady=(0, 5)
        )
        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        self._running_text = tk.Text(
            left_frame,
            wrap="none",
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="#ffffff",
            font=("Courier", 11),
            cursor="arrow",
        )
        self._running_text.grid(row=0, column=0, sticky="nsew")

        running_vsb = ctk.CTkScrollbar(
            left_frame, command=self._on_lr_yscroll
        )
        running_vsb.grid(row=0, column=1, sticky="ns")
        self._running_text.config(yscrollcommand=running_vsb.set)

        running_hsb = ctk.CTkScrollbar(
            left_frame,
            command=self._running_text.xview,
            orientation="horizontal",
        )
        running_hsb.grid(row=1, column=0, sticky="ew")
        self._running_text.config(xscrollcommand=running_hsb.set)

        # 中央: change
        center_frame = ctk.CTkFrame(main_frame)
        center_frame.grid(
            row=1, column=1, sticky="nsew", padx=(2, 2), pady=(0, 5)
        )
        center_frame.grid_rowconfigure(0, weight=1)
        center_frame.grid_columnconfigure(0, weight=1)

        self._change_text = tk.Text(
            center_frame,
            wrap="none",
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="#ffffff",
            font=("Courier", 11),
            cursor="arrow",
        )
        self._change_text.grid(row=0, column=0, sticky="nsew")
        self._change_text.bind("<Button-1>", self._on_change_click)

        change_vsb = ctk.CTkScrollbar(
            center_frame, command=self._change_text.yview
        )
        change_vsb.grid(row=0, column=1, sticky="ns")
        self._change_text.config(yscrollcommand=change_vsb.set)

        change_hsb = ctk.CTkScrollbar(
            center_frame,
            command=self._change_text.xview,
            orientation="horizontal",
        )
        change_hsb.grid(row=1, column=0, sticky="ew")
        self._change_text.config(xscrollcommand=change_hsb.set)

        # 右: expected
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.grid(
            row=1, column=2, sticky="nsew", padx=(2, 5), pady=(0, 5)
        )
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        self._expected_text = tk.Text(
            right_frame,
            wrap="none",
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="#ffffff",
            font=("Courier", 11),
            cursor="arrow",
        )
        self._expected_text.grid(row=0, column=0, sticky="nsew")

        expected_vsb = ctk.CTkScrollbar(
            right_frame, command=self._on_lr_yscroll
        )
        expected_vsb.grid(row=0, column=1, sticky="ns")
        self._expected_text.config(yscrollcommand=expected_vsb.set)

        expected_hsb = ctk.CTkScrollbar(
            right_frame,
            command=self._expected_text.xview,
            orientation="horizontal",
        )
        expected_hsb.grid(row=1, column=0, sticky="ew")
        self._expected_text.config(xscrollcommand=expected_hsb.set)

        # タグ設定
        self._configure_tags()

    def _configure_tags(self) -> None:
        """テキストウィジェットのハイライトタグを設定する。"""
        # running列: 変更由来の削除行（黄色）
        self._running_text.tag_configure(
            "change_remove",
            background="#4d4000",
            foreground="#ffe066",
        )
        # running列: 変更由来でない削除行（赤 = 検証エラー）
        self._running_text.tag_configure(
            "remove",
            background="#4d1f1f",
            foreground="#ff6b6b",
        )
        # running列: 順番違い（オレンジ）
        self._running_text.tag_configure(
            "reorder",
            background="#4d3b1f",
            foreground="#ffb347",
        )
        # running列: 空行パディング
        self._running_text.tag_configure(
            "empty", background="#1a1a1a"
        )
        # running列: クリック選択中の濃い黄色
        self._running_text.tag_configure(
            "active",
            background="#7a5a1a",
            foreground="#ffe680",
        )
        self._running_text.tag_configure(
            "delete_char", background="#8b0000", foreground="#ffffff"
        )

        # expected列: 変更由来の追加行（黄色）
        self._expected_text.tag_configure(
            "change_add",
            background="#4d4000",
            foreground="#ffe066",
        )
        # expected列: 変更由来でない追加行（緑 = 検証エラー）
        self._expected_text.tag_configure(
            "add",
            background="#1f4d1f",
            foreground="#6bff6b",
        )
        # expected列: 順番違い（オレンジ）
        self._expected_text.tag_configure(
            "reorder",
            background="#4d3b1f",
            foreground="#ffb347",
        )
        # expected列: 空行パディング
        self._expected_text.tag_configure(
            "empty", background="#1a1a1a"
        )
        # expected列: クリック選択中の濃い黄色
        self._expected_text.tag_configure(
            "active",
            background="#7a5a1a",
            foreground="#ffe680",
        )
        self._expected_text.tag_configure(
            "insert_char", background="#006400", foreground="#ffffff"
        )

        # change列: 差分対応行（黄色）
        self._change_text.tag_configure(
            "change",
            background="#4d4000",
            foreground="#ffe066",
        )
        # change列: クリック選択中の濃い黄色
        self._change_text.tag_configure(
            "active",
            background="#7a5a1a",
            foreground="#ffe680",
        )

        # タグ優先順位: active を最前面に
        for w in (
            self._running_text,
            self._change_text,
            self._expected_text,
        ):
            w.tag_raise("active")
        self._running_text.tag_raise("delete_char")
        self._expected_text.tag_raise("insert_char")

    def _create_status_bar(self) -> None:
        """ステータスバーを構築する。"""
        self._status_bar = ctk.CTkLabel(
            self,
            text="ファイルを3つ選択してValidateを実行してください",
            anchor="w",
        )
        self._status_bar.grid(
            row=2, column=0, sticky="ew", padx=10, pady=(0, 5)
        )

    # ------------------------------------------------------------------
    # スクロール同期
    # ------------------------------------------------------------------

    def _on_lr_yscroll(self, *args: object) -> None:
        """running / expected の縦スクロールを同期する。"""
        self._running_text.yview(*args)
        self._expected_text.yview(*args)

    # ------------------------------------------------------------------
    # ファイル選択
    # ------------------------------------------------------------------

    def _open_running_config(self) -> None:
        """現在のrunning-configファイルを選択する。"""
        path = filedialog.askopenfilename(
            title="現在のrunning-configを選択",
            filetypes=[
                ("テキストファイル", "*.txt"),
                ("設定ファイル", "*.conf *.cfg"),
                ("全てのファイル", "*.*"),
            ],
        )
        if not path:
            return
        self._running_path = path
        self._running_label.configure(
            text=f"Running Config: {path.split('/')[-1]}"
        )
        self._status_bar.configure(
            text=f"Running Configを読み込みました: {path}"
        )

    def _open_change_config(self) -> None:
        """設定変更内容のファイルを選択する。"""
        path = filedialog.askopenfilename(
            title="設定変更内容を選択",
            filetypes=[
                ("テキストファイル", "*.txt"),
                ("設定ファイル", "*.conf *.cfg"),
                ("全てのファイル", "*.*"),
            ],
        )
        if not path:
            return
        self._change_path = path
        self._change_label.configure(
            text=f"Change Config: {path.split('/')[-1]}"
        )
        self._status_bar.configure(
            text=f"Change Configを読み込みました: {path}"
        )

    def _open_expected_config(self) -> None:
        """想定されるrunning-configファイルを選択する。"""
        path = filedialog.askopenfilename(
            title="想定されるrunning-configを選択",
            filetypes=[
                ("テキストファイル", "*.txt"),
                ("設定ファイル", "*.conf *.cfg"),
                ("全てのファイル", "*.*"),
            ],
        )
        if not path:
            return
        self._expected_path = path
        self._expected_label.configure(
            text=f"Expected Config: {path.split('/')[-1]}"
        )
        self._status_bar.configure(
            text=f"Expected Configを読み込みました: {path}"
        )

    # ------------------------------------------------------------------
    # バリデーション実行
    # ------------------------------------------------------------------

    def _on_validate(self) -> None:
        """Validateボタン押下時にファイルを読み込んで検証を実行する。"""
        if not self._running_path:
            self._status_bar.configure(
                text="エラー: Running Configを選択してください"
            )
            return
        if not self._change_path:
            self._status_bar.configure(
                text="エラー: Change Configを選択してください"
            )
            return
        if not self._expected_path:
            self._status_bar.configure(
                text="エラー: Expected Configを選択してください"
            )
            return

        try:
            running_text = self._read_file(self._running_path)
            change_text = self._read_file(self._change_path)
            expected_text = self._read_file(self._expected_path)
        except OSError as e:
            self._status_bar.configure(
                text=f"ファイル読み込みエラー: {e}"
            )
            return

        try:
            platform = _PLATFORM_MAP[self._platform_combobox.get()]
            self._result = validate(
                running_text, change_text, expected_text, platform
            )
        except Exception as e:  # noqa: BLE001
            self._status_bar.configure(text=f"解析エラー: {e!s}")
            return

        self._active_change_idx = -1
        self._active_running_rows = []
        self._active_expected_rows = []
        self._render_result()

    def _read_file(self, path: str) -> str:
        """ファイルを読み込んでテキストを返す。

        Args:
            path: ファイルパス

        Returns:
            ファイルのテキスト内容
        """
        with open(path, encoding="utf-8") as f:
            return f.read()

    # ------------------------------------------------------------------
    # 描画
    # ------------------------------------------------------------------

    def _render_result(self) -> None:
        """検証結果をテキストエリアに反映する。"""
        if self._result is None:
            return

        result = self._result

        # 全テキストエリアをクリア
        for w in (
            self._running_text,
            self._change_text,
            self._expected_text,
        ):
            w.delete("1.0", "end")

        # 行番号付きで各列を描画
        for row, (line, rtype) in enumerate(
            zip(result.running_lines, result.running_types), start=1
        ):
            line_num = f"{row:{_LINE_NUM_WIDTH - 1}d} "
            self._running_text.insert("end", line_num + line + "\n")
            if rtype != "equal":
                self._running_text.tag_add(rtype, f"{row}.0", f"{row}.end")

        for row, (line, etype) in enumerate(
            zip(result.expected_lines, result.expected_types), start=1
        ):
            line_num = f"{row:{_LINE_NUM_WIDTH - 1}d} "
            self._expected_text.insert("end", line_num + line + "\n")
            if etype != "equal":
                self._expected_text.tag_add(etype, f"{row}.0", f"{row}.end")

        for ci, (line, ctype) in enumerate(
            zip(result.change_lines, result.change_types)
        ):
            row = ci + 1
            line_num = f"{row:{_LINE_NUM_WIDTH - 1}d} "
            self._change_text.insert("end", line_num + line + "\n")
            if ctype == "change":
                self._change_text.tag_add("change", f"{row}.0", f"{row}.end")

        # 文字単位インライン差分（change_remove ↔ change_add の対応行間）
        self._apply_inline_char_diffs(result)

        # ステータスバーを更新
        change_remove_count = result.running_types.count("change_remove")
        change_add_count = result.expected_types.count("change_add")
        remove_count = result.running_types.count("remove")
        add_count = result.expected_types.count("add")

        if result.is_valid:
            self._status_bar.configure(
                text=(
                    f"✓ 検証成功: 全ての差分が設定変更内容由来です "
                    f"（削除: {change_remove_count}行, "
                    f"追加: {change_add_count}行）"
                    " ／ 設定変更内容の黄色行をクリックすると対応行へジャンプ"
                )
            )
        else:
            self._status_bar.configure(
                text=(
                    f"✗ 検証エラー: 説明できない差分があります "
                    f"（未説明削除: {remove_count}行, "
                    f"未説明追加: {add_count}行）"
                    " ／ 黄色行をクリックすると対応行へジャンプ"
                )
            )

    def _apply_inline_char_diffs(self, result: ValidateResult) -> None:
        """change_remove と change_add の対応行間で文字単位差分を強調する。

        change_to_running と change_to_expected を使い、
        同じ change 行インデックスに対応する running / expected 行を
        ペアリングして文字単位差分を計算する。

        Args:
            result: 検証結果
        """
        for ci, ci_run_rows in result.change_to_running.items():
            ci_exp_rows = result.change_to_expected.get(ci, [])
            if not ci_run_rows or not ci_exp_rows:
                continue

            for run_r, exp_r in zip(ci_run_rows, ci_exp_rows):
                src_line = result.running_lines[run_r - 1]
                tgt_line = result.expected_lines[exp_r - 1]
                if not src_line or not tgt_line:
                    continue

                ratio = difflib.SequenceMatcher(
                    None, src_line, tgt_line, autojunk=False
                ).ratio()
                if ratio < _INLINE_DIFF_THRESHOLD:
                    continue

                matcher = difflib.SequenceMatcher(
                    None, src_line, tgt_line, autojunk=False
                )
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag in ("replace", "delete"):
                        self._running_text.tag_add(
                            "delete_char",
                            f"{run_r}.{i1 + _LINE_NUM_WIDTH}",
                            f"{run_r}.{i2 + _LINE_NUM_WIDTH}",
                        )
                    if tag in ("replace", "insert"):
                        self._expected_text.tag_add(
                            "insert_char",
                            f"{exp_r}.{j1 + _LINE_NUM_WIDTH}",
                            f"{exp_r}.{j2 + _LINE_NUM_WIDTH}",
                        )

    # ------------------------------------------------------------------
    # クリックハンドラ
    # ------------------------------------------------------------------

    def _on_change_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """設定変更内容の行クリック時の処理。

        クリックした行が "change" タイプの場合、対応する running /
        expected 行を濃い黄色でハイライトしスクロールで表示する。

        Args:
            event: マウスクリックイベント
        """
        if self._result is None:
            return

        row = int(
            self._change_text.index(f"@{event.x},{event.y}").split(".")[0]
        )
        ci = row - 1  # 0ベースのchange行インデックス

        if ci < 0 or ci >= len(self._result.change_types):
            return

        # change タイプでない行はスキップ
        if self._result.change_types[ci] != "change":
            return

        # 前回のアクティブハイライトをリセット
        self._clear_active_highlights()

        if ci == self._active_change_idx:
            # 同じ行を再クリック → ハイライト解除のみ
            self._active_change_idx = -1
            return

        self._active_change_idx = ci

        # change列のアクティブ行をハイライト
        self._change_text.tag_add("active", f"{row}.0", f"{row}.end")

        # running列の対応行をハイライト＆スクロール
        running_rows = self._result.change_to_running.get(ci, [])
        for r in running_rows:
            self._running_text.tag_add("active", f"{r}.0", f"{r}.end")
            self._active_running_rows.append(r)
        if running_rows:
            self._running_text.see(f"{running_rows[0]}.0")
            self._expected_text.see(f"{running_rows[0]}.0")

        # expected列の対応行をハイライト
        expected_rows = self._result.change_to_expected.get(ci, [])
        for r in expected_rows:
            self._expected_text.tag_add("active", f"{r}.0", f"{r}.end")
            self._active_expected_rows.append(r)
        if expected_rows and not running_rows:
            # running に対応行がない場合は expected 側でスクロール
            self._expected_text.see(f"{expected_rows[0]}.0")
            self._running_text.see(f"{expected_rows[0]}.0")

    def _clear_active_highlights(self) -> None:
        """全テキストエリアのアクティブハイライトを解除する。"""
        self._running_text.tag_remove("active", "1.0", "end")
        self._change_text.tag_remove("active", "1.0", "end")
        self._expected_text.tag_remove("active", "1.0", "end")
        self._active_running_rows = []
        self._active_expected_rows = []
