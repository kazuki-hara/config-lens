"""WinMerge ライクな統合比較ビューモジュール。

UI レイアウト（全モード共通）:
- row=0: ツールバー（Platform / Compare / リセット）
- row=1: パスバー — grid + uniform で Left/Right を常に厳密 50/50
- row=2: ドロップゾーン（初期）or 列ヘッダー（フォルダ比較時 weight=0）
- row=3: スクロール一覧（フォルダ比較時 weight=1）
- row=4: フリーペアバー（フォルダ比較中のみ）
- row=5: ステータスバー
"""

from __future__ import annotations

import re
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from tkinterdnd2 import DND_FILES

from src.compare.folder_logic import FileDiffEntry, FolderDiffScanner
from src.compare.platforms import PLATFORM_MAP
from src.compare.result_window import CompareResultWindow
from src.compare.settings import AppSettings

_PLATFORM_MAP = PLATFORM_MAP

_STATUS_CONFIG: dict[str, dict[str, str]] = {
    "same":       {"icon": "  =  ", "fg": "#888888", "bg": "#2b2b2b"},
    "diff":       {"icon": "  ≠  ", "fg": "#ffd966", "bg": "#4d3800"},
    "only_left":  {"icon": "  ←  ", "fg": "#aaaaaa", "bg": "#383838"},
    "only_right": {"icon": "  →  ", "fg": "#aaaaaa", "bg": "#383838"},
}

_ZONE_NORMAL = "#1e1e1e"
_ZONE_HOVER  = "#003366"
_ZONE_SET    = "#1a2e1a"


def _parse_dnd_data(raw: str) -> Path | None:
    """tkinterdnd2 の Drop イベントデータから最初のパスを抽出する。"""
    raw = raw.strip()
    m = re.findall(r"\{([^}]+)\}", raw)
    if m:
        return Path(m[0])
    parts = raw.split()
    return Path(parts[0]) if parts else None


# ---------------------------------------------------------------------------
# _PathBar — パスバー（常に Left/Right 厳密 50/50）
# ---------------------------------------------------------------------------

class _PathBar(ctk.CTkFrame):
    """パスバー: grid + uniform で Left/Right を 50/50 に固定する。"""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        on_left_file: Callable[[], None],
        on_left_folder: Callable[[], None],
        on_right_file: Callable[[], None],
        on_right_folder: Callable[[], None],
    ) -> None:
        super().__init__(parent, fg_color="#252525", height=40, corner_radius=0)
        self.grid_propagate(False)

        # col=0 (Left, weight=1, uniform="h") | col=1 (divider) | col=2 (Right, weight=1, uniform="h")
        # uniform="h" が同グループを同幅に強制する
        self.grid_columnconfigure(0, weight=1, uniform="h")
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1, uniform="h")
        self.grid_rowconfigure(0, weight=1)

        # ---- Left 側 ----
        left_f = ctk.CTkFrame(self, fg_color="transparent")
        left_f.grid(row=0, column=0, sticky="nsew")
        left_f.grid_columnconfigure(1, weight=1)  # パスラベルが残り幅を埋める

        ctk.CTkLabel(
            left_f, text="Left:", text_color="#888888", width=42, anchor="e",
        ).grid(row=0, column=0, padx=(8, 2), sticky="ew")

        self._left_label = ctk.CTkLabel(
            left_f, text="(未選択)", anchor="w", text_color="#888888",
        )
        self._left_label.grid(row=0, column=1, sticky="ew")

        ctk.CTkButton(
            left_f, text="ファイル", width=60, height=26,
            fg_color="#3a3a3a", hover_color="#555555", command=on_left_file,
        ).grid(row=0, column=2, padx=2, pady=7)
        ctk.CTkButton(
            left_f, text="フォルダ", width=60, height=26,
            fg_color="#3a3a3a", hover_color="#555555", command=on_left_folder,
        ).grid(row=0, column=3, padx=(2, 6), pady=7)

        # ---- 縦区切り ----
        ctk.CTkFrame(self, width=1, fg_color="#555555").grid(
            row=0, column=1, sticky="ns", pady=6
        )

        # ---- Right 側 ----
        right_f = ctk.CTkFrame(self, fg_color="transparent")
        right_f.grid(row=0, column=2, sticky="nsew")
        right_f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            right_f, text="Right:", text_color="#888888", width=46, anchor="e",
        ).grid(row=0, column=0, padx=(8, 2), sticky="ew")

        self._right_label = ctk.CTkLabel(
            right_f, text="(未選択)", anchor="w", text_color="#888888",
        )
        self._right_label.grid(row=0, column=1, sticky="ew")

        ctk.CTkButton(
            right_f, text="ファイル", width=60, height=26,
            fg_color="#3a3a3a", hover_color="#555555", command=on_right_file,
        ).grid(row=0, column=2, padx=2, pady=7)
        ctk.CTkButton(
            right_f, text="フォルダ", width=60, height=26,
            fg_color="#3a3a3a", hover_color="#555555", command=on_right_folder,
        ).grid(row=0, column=3, padx=(2, 8), pady=7)

    def set_left(self, path: Path) -> None:
        self._left_label.configure(text=str(path), text_color="#cccccc")

    def set_right(self, path: Path) -> None:
        self._right_label.configure(text=str(path), text_color="#cccccc")

    def clear_left(self) -> None:
        self._left_label.configure(text="(未選択)", text_color="#888888")

    def clear_right(self) -> None:
        self._right_label.configure(text="(未選択)", text_color="#888888")


# ---------------------------------------------------------------------------
# _DropZone
# ---------------------------------------------------------------------------

class _DropZone(ctk.CTkFrame):
    """大きな明示的ドロップゾーン。"""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        side_label: str,
        callback: Callable[[Path], None],
    ) -> None:
        super().__init__(
            parent,
            corner_radius=12,
            fg_color=_ZONE_NORMAL,
            border_width=2,
            border_color="#444444",
        )
        self._side_label = side_label
        self._callback = callback
        self._path: Path | None = None
        self._build()
        self._register_dnd()

    def _build(self) -> None:
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(inner, text="⊕", font=ctk.CTkFont(size=40), text_color="#555555").pack()
        ctk.CTkLabel(
            inner, text=self._side_label,
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#aaaaaa",
        ).pack(pady=(4, 2))
        ctk.CTkLabel(
            inner,
            text="ファイル / フォルダをドロップ\nまたは上のボタンで選択",
            font=ctk.CTkFont(size=12), text_color="#666666", justify="center",
        ).pack()

        for w in (self, inner):
            w.bind("<Button-1>", self._on_click, add="+")  # type: ignore[arg-type]
        for child in inner.winfo_children():
            child.bind("<Button-1>", self._on_click, add="+")  # type: ignore[arg-type]

    def _register_dnd(self) -> None:
        self.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
        self.dnd_bind("<<DragEnter>>", self._on_drag_enter)  # type: ignore[attr-defined]
        self.dnd_bind("<<DragLeave>>", self._on_drag_leave)  # type: ignore[attr-defined]
        self.dnd_bind("<<Drop>>",      self._on_drop)        # type: ignore[attr-defined]

    def _on_drag_enter(self, _: tk.Event) -> None:  # type: ignore[type-arg]
        self.configure(fg_color=_ZONE_HOVER, border_color="#4488ff")

    def _on_drag_leave(self, _: tk.Event) -> None:  # type: ignore[type-arg]
        self.configure(
            fg_color=_ZONE_NORMAL if self._path is None else _ZONE_SET,
            border_color="#444444" if self._path is None else "#44aa44",
        )

    def _on_drop(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        path = _parse_dnd_data(event.data)  # type: ignore[attr-defined]
        if path is not None:
            self.set_path(path)

    def _on_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="ファイルを選択...", command=self.browse_file)
        menu.add_command(label="フォルダを選択...", command=self.browse_folder)
        menu.tk_popup(event.x_root, event.y_root)

    def browse_file(self) -> None:
        p = filedialog.askopenfilename(title=f"{self._side_label} ファイルを選択")
        if p:
            self.set_path(Path(p))

    def browse_folder(self) -> None:
        p = filedialog.askdirectory(title=f"{self._side_label} フォルダを選択")
        if p:
            self.set_path(Path(p))

    def set_path(self, path: Path) -> None:
        self._path = path
        self.configure(fg_color=_ZONE_SET, border_color="#44aa44")
        self._callback(path)

    def get_path(self) -> Path | None:
        return self._path

    def reset(self) -> None:
        self._path = None
        self.configure(fg_color=_ZONE_NORMAL, border_color="#444444")


# ---------------------------------------------------------------------------
# OpenView
# ---------------------------------------------------------------------------

class OpenView(ctk.CTkFrame):
    """ファイル/フォルダ兼用の比較開始 UI フレーム。"""

    def __init__(
        self,
        parent: ctk.CTk | ctk.CTkBaseClass,
        settings: AppSettings,
    ) -> None:
        super().__init__(parent, corner_radius=0, fg_color="transparent")
        self._settings = settings
        self._entries: list[FileDiffEntry] = []
        self._scanner = FolderDiffScanner(walk_depth=1)
        self._result_windows: dict[str, CompareResultWindow] = {}
        self._free_left: Path | None = None
        self._free_right: Path | None = None
        self._create_widgets()

    # ------------------------------------------------------------------
    # UI 構築
    # ------------------------------------------------------------------

    def _create_widgets(self) -> None:
        # 初期状態: row=2 がドロップゾーン（weight=1）、row=3 は未使用
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ================================================================
        # row=0: ツールバー
        # ================================================================
        toolbar = ctk.CTkFrame(self, fg_color="#2b2b2b", height=42, corner_radius=0)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_propagate(False)

        ctk.CTkLabel(toolbar, text="Platform:").pack(side="left", padx=(12, 4))
        self._platform_box = ctk.CTkComboBox(
            toolbar, values=list(_PLATFORM_MAP.keys()), width=160, state="readonly",
        )
        self._platform_box.set("CISCO_IOS")
        self._platform_box.pack(side="left", pady=6)

        ctk.CTkButton(
            toolbar, text="リセット", command=self._on_reset,
            width=70, fg_color="#555555", hover_color="#333333",
        ).pack(side="right", padx=(0, 12), pady=6)

        ctk.CTkButton(
            toolbar, text="Compare", command=self._on_compare,
            width=100, fg_color="green", hover_color="darkgreen",
        ).pack(side="right", padx=(0, 4), pady=6)

        # ================================================================
        # row=1: パスバー（_PathBar が grid + uniform で 50/50 を保証）
        # ================================================================
        self._path_bar = _PathBar(
            self,
            on_left_file=lambda: self._left_zone.browse_file(),
            on_left_folder=lambda: self._left_zone.browse_folder(),
            on_right_file=lambda: self._right_zone.browse_file(),
            on_right_folder=lambda: self._right_zone.browse_folder(),
        )
        self._path_bar.grid(row=1, column=0, sticky="ew")

        # ================================================================
        # row=2: ドロップゾーン（初期表示）
        # ================================================================
        self._main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._main_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        self._main_frame.grid_rowconfigure(0, weight=1)
        self._main_frame.grid_columnconfigure(0, weight=1, uniform="dz")
        self._main_frame.grid_columnconfigure(1, weight=1, uniform="dz")

        self._left_zone = _DropZone(self._main_frame, "Left", self._on_left_path)
        self._left_zone.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self._right_zone = _DropZone(self._main_frame, "Right", self._on_right_path)
        self._right_zone.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # ================================================================
        # row=2 (フォルダ時): 列ヘッダーバー（フォルダパスは上部パスバーに表示済み）
        # ================================================================
        self._col_header = ctk.CTkFrame(self, fg_color="#2a2a2a", height=30, corner_radius=0)
        self._col_header.grid_propagate(False)
        # 列構成: status(固定) | left_name(可変) | right_name(可変) | diff(固定) | btns(固定)
        self._col_header.grid_columnconfigure(0, weight=0)
        self._col_header.grid_columnconfigure(1, weight=1, uniform="col")
        self._col_header.grid_columnconfigure(2, weight=1, uniform="col")
        self._col_header.grid_columnconfigure(3, weight=0)
        self._col_header.grid_columnconfigure(4, weight=0)
        self._col_header.grid_rowconfigure(0, weight=1)

        hfont = ctk.CTkFont(size=11, weight="bold")
        ctk.CTkLabel(self._col_header, text="状態", font=hfont, text_color="#666666", width=56).grid(
            row=0, column=0, padx=(8, 2), sticky="w"
        )
        ctk.CTkLabel(self._col_header, text="ファイル名 (Left)", font=hfont, text_color="#666666", anchor="w").grid(
            row=0, column=1, padx=4, sticky="ew"
        )
        ctk.CTkLabel(self._col_header, text="ファイル名 (Right)", font=hfont, text_color="#666666", anchor="w").grid(
            row=0, column=2, padx=4, sticky="ew"
        )
        ctk.CTkLabel(self._col_header, text="比較", font=hfont, text_color="#666666", width=56).grid(
            row=0, column=3, padx=4, sticky="w"
        )
        ctk.CTkLabel(self._col_header, text="← 左 / 右 →", font=hfont, text_color="#666666", width=126).grid(
            row=0, column=4, padx=(4, 8), sticky="w"
        )

        # ================================================================
        # row=3 (フォルダ時): スクロール一覧
        # ================================================================
        self._list_frame = ctk.CTkScrollableFrame(self, label_text="", corner_radius=0)
        self._list_frame.grid_columnconfigure(0, weight=0)   # 状態
        self._list_frame.grid_columnconfigure(1, weight=1, uniform="lc")   # 左ファイル名
        self._list_frame.grid_columnconfigure(2, weight=1, uniform="lc")   # 右ファイル名
        self._list_frame.grid_columnconfigure(3, weight=0)   # diff
        self._list_frame.grid_columnconfigure(4, weight=0)   # ←左に
        self._list_frame.grid_columnconfigure(5, weight=0)   # 右に→

        # ================================================================
        # row=4 (フォルダ時): フリーペアバー
        # ================================================================
        self._free_bar = ctk.CTkFrame(self, fg_color="#2b2b2b", height=38, corner_radius=0)
        self._free_bar.grid_propagate(False)
        self._free_bar.grid_columnconfigure(0, weight=1, uniform="fb")
        self._free_bar.grid_columnconfigure(1, weight=0)
        self._free_bar.grid_columnconfigure(2, weight=1, uniform="fb")
        self._free_bar.grid_columnconfigure(3, weight=0)
        self._free_bar.grid_rowconfigure(0, weight=1)

        # 左選択表示
        left_sel = ctk.CTkFrame(self._free_bar, fg_color="transparent")
        left_sel.grid(row=0, column=0, sticky="nsew", padx=(10, 4))
        left_sel.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(left_sel, text="← 左:", text_color="#888888", width=40, anchor="e").grid(
            row=0, column=0, sticky="ew"
        )
        self._free_left_label = ctk.CTkLabel(
            left_sel, text="(未選択)", anchor="w", text_color="#555555",
        )
        self._free_left_label.grid(row=0, column=1, sticky="ew")

        # 縦区切り
        ctk.CTkFrame(self._free_bar, width=1, fg_color="#444444").grid(
            row=0, column=1, sticky="ns", pady=6
        )

        # 右選択表示
        right_sel = ctk.CTkFrame(self._free_bar, fg_color="transparent")
        right_sel.grid(row=0, column=2, sticky="nsew", padx=(8, 4))
        right_sel.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(right_sel, text="右 →:", text_color="#888888", width=40, anchor="e").grid(
            row=0, column=0, sticky="ew"
        )
        self._free_right_label = ctk.CTkLabel(
            right_sel, text="(未選択)", anchor="w", text_color="#555555",
        )
        self._free_right_label.grid(row=0, column=1, sticky="ew")

        # 比較ボタン
        self._free_compare_btn = ctk.CTkButton(
            self._free_bar, text="選択ペアを比較", command=self._on_free_compare,
            width=120, fg_color="#444444", hover_color="#555555", state="disabled",
        )
        self._free_compare_btn.grid(row=0, column=3, padx=10, pady=6)

        # ================================================================
        # row=5: ステータスバー
        # ================================================================
        self._stats_bar = ctk.CTkLabel(
            self,
            text="ファイルまたはフォルダをドロップ、またはボタンで選択してください",
            anchor="w", text_color="#888888",
        )
        self._stats_bar.grid(row=5, column=0, sticky="ew", padx=8, pady=(0, 4))

    # ------------------------------------------------------------------
    # モード切替ヘルパー
    # ------------------------------------------------------------------

    def _show_drop_mode(self) -> None:
        """ドロップゾーン画面を表示する。"""
        self._col_header.grid_remove()
        self._list_frame.grid_remove()
        self._free_bar.grid_remove()
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=0)
        self._main_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)

    def _show_folder_mode(self) -> None:
        """フォルダ比較一覧を表示する。"""
        self._main_frame.grid_remove()
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)
        self._col_header.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 0))
        self._list_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=0)
        self._free_bar.grid(row=4, column=0, sticky="ew", padx=8, pady=(2, 2))

    # ------------------------------------------------------------------
    # コールバック
    # ------------------------------------------------------------------

    def _on_left_path(self, path: Path) -> None:
        self._settings.update(["open_view", "last_left"], str(path))
        self._path_bar.set_left(path)
        self._maybe_auto_compare()

    def _on_right_path(self, path: Path) -> None:
        self._settings.update(["open_view", "last_right"], str(path))
        self._path_bar.set_right(path)
        self._maybe_auto_compare()

    def _maybe_auto_compare(self) -> None:
        left  = self._left_zone.get_path()
        right = self._right_zone.get_path()
        if left is not None and right is not None and left.is_dir() and right.is_dir():
            self._run_folder_compare(left, right)

    def _on_reset(self) -> None:
        self._left_zone.reset()
        self._right_zone.reset()
        self._path_bar.clear_left()
        self._path_bar.clear_right()
        self._entries = []
        self._free_left = None
        self._free_right = None
        self._free_left_label.configure(text="(未選択)", text_color="#555555")
        self._free_right_label.configure(text="(未選択)", text_color="#555555")
        self._update_free_compare_btn()
        self._show_drop_mode()
        self._stats_bar.configure(
            text="ファイルまたはフォルダをドロップ、またはボタンで選択してください",
            text_color="#888888",
        )

    def _on_compare(self) -> None:
        left  = self._left_zone.get_path()
        right = self._right_zone.get_path()
        if left is None or right is None:
            self._stats_bar.configure(
                text="⚠ 左右のパスを両方選択してください", text_color="#ff8888"
            )
            return
        if left.is_dir() and right.is_dir():
            self._run_folder_compare(left, right)
        elif left.is_file() and right.is_file():
            self._open_file_compare(left, right)
        else:
            self._stats_bar.configure(
                text="⚠ 左右は同じ種類（ファイル同士またはフォルダ同士）を選択してください",
                text_color="#ff8888",
            )

    def _on_free_compare(self) -> None:
        if self._free_left is not None and self._free_right is not None:
            self._open_file_compare(self._free_left, self._free_right)

    def _set_free_left(self, path: Path) -> None:
        self._free_left = path
        self._free_left_label.configure(text=path.name, text_color="#88cc88")
        self._update_free_compare_btn()

    def _set_free_right(self, path: Path) -> None:
        self._free_right = path
        self._free_right_label.configure(text=path.name, text_color="#88cc88")
        self._update_free_compare_btn()

    def _update_free_compare_btn(self) -> None:
        if self._free_left is not None and self._free_right is not None:
            self._free_compare_btn.configure(
                state="normal", fg_color="green", hover_color="darkgreen",
            )
        else:
            self._free_compare_btn.configure(
                state="disabled", fg_color="#444444", hover_color="#555555",
            )

    # ------------------------------------------------------------------
    # 比較処理
    # ------------------------------------------------------------------

    def _run_folder_compare(self, left: Path, right: Path) -> None:
        """フォルダ比較を実行してインライン一覧を表示する。"""
        self._entries = self._scanner.scan(left, right)
        self._free_left = None
        self._free_right = None
        self._free_left_label.configure(text="(未選択)", text_color="#555555")
        self._free_right_label.configure(text="(未選択)", text_color="#555555")
        self._update_free_compare_btn()
        self._show_folder_mode()

        # 既存行を削除（row=0 のヘッダーは残す）
        for w in list(self._list_frame.winfo_children()):
            info = w.grid_info()  # type: ignore[union-attr]
            if info and int(info.get("row", 0)) >= 0:
                w.destroy()

        counts: dict[str, int] = {"diff": 0, "same": 0, "only_left": 0, "only_right": 0}
        for row_idx, entry in enumerate(self._entries):
            counts[entry.status] = counts.get(entry.status, 0) + 1
            cfg        = _STATUS_CONFIG.get(entry.status, _STATUS_CONFIG["same"])
            left_name  = entry.left_path.name  if entry.left_path  else ""
            right_name = entry.right_path.name if entry.right_path else ""

            # 状態アイコン
            ctk.CTkLabel(
                self._list_frame, text=cfg["icon"],
                text_color=cfg["fg"], fg_color=cfg["bg"],
                corner_radius=4, width=56,
            ).grid(row=row_idx, column=0, padx=(8, 2), pady=2, sticky="w")

            # 左ファイル名
            ctk.CTkLabel(
                self._list_frame,
                text=left_name or "---", anchor="w",
                text_color=cfg["fg"] if left_name else "#555555",
            ).grid(row=row_idx, column=1, padx=4, pady=2, sticky="ew")

            # 右ファイル名
            ctk.CTkLabel(
                self._list_frame,
                text=right_name or "---", anchor="w",
                text_color=cfg["fg"] if right_name else "#555555",
            ).grid(row=row_idx, column=2, padx=4, pady=2, sticky="ew")

            # diff ボタン (same ペアのみ非表示)
            if entry.status == "diff" and entry.left_path and entry.right_path:
                ctk.CTkButton(
                    self._list_frame, text="diff", width=56,
                    command=lambda lp=entry.left_path, rp=entry.right_path: (
                        self._open_file_compare(lp, rp)
                    ),
                ).grid(row=row_idx, column=3, padx=4, pady=2)
            else:
                ctk.CTkLabel(self._list_frame, text="", width=56).grid(
                    row=row_idx, column=3, padx=4
                )

            # ←左に ボタン
            if entry.left_path:
                lpath = entry.left_path
                ctk.CTkButton(
                    self._list_frame, text="←左に", width=60, height=24,
                    fg_color="#3a3a3a", hover_color="#4a5f4a",
                    command=lambda p=lpath: self._set_free_left(p),
                ).grid(row=row_idx, column=4, padx=4, pady=2)
            else:
                ctk.CTkLabel(self._list_frame, text="", width=60).grid(
                    row=row_idx, column=4, padx=4
                )

            # 右に→ ボタン
            if entry.right_path:
                rpath = entry.right_path
                ctk.CTkButton(
                    self._list_frame, text="右に→", width=60, height=24,
                    fg_color="#3a3a3a", hover_color="#4a5f4a",
                    command=lambda p=rpath: self._set_free_right(p),
                ).grid(row=row_idx, column=5, padx=(4, 8), pady=2)
            else:
                ctk.CTkLabel(self._list_frame, text="", width=60).grid(
                    row=row_idx, column=5, padx=(4, 8)
                )

        stats = (
            f"合計 {len(self._entries)} 件 — "
            f"差分: {counts['diff']} / 同一: {counts['same']} / "
            f"左のみ: {counts['only_left']} / 右のみ: {counts['only_right']}"
        )
        self._stats_bar.configure(text=stats, text_color="#aaaaaa")

    def _open_file_compare(self, left: Path, right: Path) -> None:
        """ファイル比較: CompareResultWindow を開く（重複防止）。"""
        platform_name = self._platform_box.get()
        key = f"{left}::{right}"
        win = self._result_windows.get(key)
        if win and win.winfo_exists():
            win.lift()
            return
        win = CompareResultWindow(self, left, right, platform_name, self._settings)
        self._result_windows[key] = win

    def reset(self) -> None:
        """新規比較のためにビューをリセットする（メニューの 新規 から呼ばれる）。"""
        self._on_reset()
