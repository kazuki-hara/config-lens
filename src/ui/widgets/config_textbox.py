"""Config表示用のカスタムテキストボックスウィジェット

このモジュールは、ネットワーク機器の設定ファイルを表示するための
カスタマイズされたテキストボックスを提供します。
特定の行をハイライトする機能を持ちます。
"""

from dataclasses import dataclass
from typing import Any, Callable, Literal

import customtkinter


@dataclass
class HighlightStyle:
    """ハイライトスタイルを定義するデータクラス
    
    Attributes:
        background: 背景色
        foreground: 文字色
        font_weight: フォント太さ（normal または bold）
    """
    background: str
    foreground: str
    font_weight: Literal["normal", "bold"] = "normal"


class ConfigTextbox(customtkinter.CTkTextbox):
    """Config表示用のカスタムテキストボックス
    
    ネットワーク機器の設定ファイルを表示し、特定の行を
    ハイライトする機能を提供します。複数のハイライトスタイルを
    サポートし、差分表示などの用途に対応します。
    
    Attributes:
        _highlight_styles: 登録されたハイライトスタイルの辞書
    """
    
    # デフォルトのハイライトスタイル定義
    DEFAULT_STYLES = {
        "default": HighlightStyle(
            background="#FFE066",
            foreground="black",
            font_weight="normal"
        ),
        "add": HighlightStyle(
            background="#C6F6D5",
            foreground="black",
            font_weight="normal"
        ),
        "remove": HighlightStyle(
            background="#FED7D7",
            foreground="black",
            font_weight="normal"
        ),
        "modify": HighlightStyle(
            background="#FEF08A",
            foreground="black",
            font_weight="bold"
        ),
        # 強調表示用スタイル（より濃い色）
        "emphasize": HighlightStyle(
            background="#FFD700",
            foreground="black",
            font_weight="bold"
        ),
        "emphasize_add": HighlightStyle(
            background="#68D391",
            foreground="black",
            font_weight="bold"
        ),
        "emphasize_remove": HighlightStyle(
            background="#FC8181",
            foreground="black",
            font_weight="bold"
        ),
    }
    
    def __init__(self, master: Any, **kwargs: Any) -> None:
        """ConfigTextboxを初期化する
        
        Args:
            master: 親ウィジェット
            **kwargs: CTkTextboxに渡す追加の引数
        """
        super().__init__(master, **kwargs)
        self._highlight_styles: dict[str, HighlightStyle] = {}
        self._initialize_default_styles()
    
    def _initialize_default_styles(self) -> None:
        """デフォルトのハイライトスタイルを初期化する"""
        for name, style in self.DEFAULT_STYLES.items():
            self.add_highlight_style(name, style)
    
    def add_highlight_style(
        self,
        name: str,
        style: HighlightStyle
    ) -> None:
        """新しいハイライトスタイルを追加する
        
        Args:
            name: スタイル名（タグ名として使用）
            style: ハイライトスタイル
        """
        self._highlight_styles[name] = style
        
        # Tkinterのタグとして設定（内部のtkinter Textウィジェットに対して）
        # Note: font_weightはtag_configでは直接設定できないため、
        # 必要に応じてfontオプション全体を設定する必要がある
        self._textbox.tag_config(
            name,
            background=style.background,
            foreground=style.foreground,
        )
    
    def set_text(self, text: str, readonly: bool = True) -> None:
        """テキストボックスにテキストを設定する
        
        Args:
            text: 表示するテキスト
            readonly: 読み取り専用にするかどうか（デフォルト: True）
        """
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.insert("1.0", text)
        
        if readonly:
            self.configure(state="disabled")
    
    def highlight_lines(
        self,
        line_numbers: list[int],
        style_name: str = "default"
    ) -> None:
        """指定された行番号のリストをハイライトする
        
        Args:
            line_numbers: ハイライトする行番号のリスト（1から始まる）
            style_name: 使用するハイライトスタイル名
            
        Raises:
            ValueError: 指定されたスタイル名が存在しない場合
        """
        if style_name not in self._highlight_styles:
            available_styles = ", ".join(self._highlight_styles.keys())
            raise ValueError(
                f"スタイル '{style_name}' が見つかりません。"
                f"利用可能なスタイル: {available_styles}"
            )
        
        # 一時的に編集可能にする（内部のtkinter Textウィジェットにアクセス）
        current_state = str(self._textbox.cget("state"))
        self.configure(state="normal")
        
        # 各行にタグを追加（内部のtkinter Textウィジェットに対して操作）
        # 改行文字も含めて行全体をハイライトするため、end+1cを使用
        for line_num in line_numbers:
            start_index = f"{line_num}.0"
            end_index = f"{line_num}.end+1c"
            self._textbox.tag_add(style_name, start_index, end_index)
        
        # 元の状態に戻す
        self.configure(state=current_state)
    
    def clear_highlights(self, style_name: str | None = None) -> None:
        """ハイライトをクリアする
        
        Args:
            style_name: クリアするスタイル名。Noneの場合はすべてクリア
        """
        # 一時的に編集可能にする（内部のtkinter Textウィジェットにアクセス）
        current_state = str(self._textbox.cget("state"))
        self.configure(state="normal")
        
        if style_name is None:
            # すべてのスタイルのハイライトをクリア
            for name in self._highlight_styles.keys():
                self._textbox.tag_remove(name, "1.0", "end")
        else:
            # 指定されたスタイルのみクリア
            if style_name in self._highlight_styles:
                self._textbox.tag_remove(style_name, "1.0", "end")
        
        # 元の状態に戻す
        self.configure(state=current_state)
    
    def get_available_styles(self) -> list[str]:
        """利用可能なハイライトスタイルのリストを取得する
        
        Returns:
            スタイル名のリスト
        """
        return list(self._highlight_styles.keys())
    
    def _bind_click_event(self) -> None:
        """行クリックイベントをバインドする"""
        self._textbox.bind("<Button-1>", self._on_click)
    
    def _on_click(self, event: Any) -> None:
        """クリックイベントのハンドラ
        
        Args:
            event: tkinterのイベントオブジェクト
        """
        # クリックされた位置から行番号を取得
        index = self._textbox.index(f"@{event.x},{event.y}")
        line_num = int(index.split(".")[0])
        
        # コールバックが設定されている場合は実行
        if self._line_click_callback:
            self._line_click_callback(line_num)
    
    def set_line_click_callback(
        self, callback: Callable[[int], None]
    ) -> None:
        """行クリック時のコールバックを設定する
        
        Args:
            callback: 行番号を引数に取るコールバック関数
        """
        self._line_click_callback = callback
    
    def get_line_at_position(self, x: int, y: int) -> int:
        """指定された座標の行番号を取得する
        
        Args:
            x: X座標
            y: Y座標
            
        Returns:
            行番号（1から始まる）
        """
        index = self._textbox.index(f"@{x},{y}")
        line_num = int(index.split(".")[0])
        return line_num
    
    def emphasize_lines(
        self,
        line_numbers: list[int],
        base_style: str = "default"
    ) -> None:
        """指定された行を強調表示する
        
        既存のハイライトを保持したまま、より強い強調を追加します。
        
        Args:
            line_numbers: 強調表示する行番号のリスト
            base_style: ベースとなるスタイル名
        """
        # 既存の強調表示をクリア
        self.clear_emphasis()
        
        # 強調スタイルを決定
        emphasize_style = f"emphasize_{base_style}"
        if emphasize_style not in self._highlight_styles:
            emphasize_style = "emphasize"
        
        # 強調表示を適用
        self.highlight_lines(line_numbers, emphasize_style)
        
        # 強調表示中の行を記録
        self._emphasized_lines = set(line_numbers)
    
    def clear_emphasis(self) -> None:
        """強調表示をクリアする"""
        if not self._emphasized_lines:
            return
        
        # 強調表示をクリア
        for style_name in ["emphasize", "emphasize_add", "emphasize_remove"]:
            self.clear_highlights(style_name)
        
        self._emphasized_lines.clear()
    
    def get_line_count(self) -> int:
        """テキストボックスの行数を取得する
        
        Returns:
            行数
        """
        return int(self._textbox.index("end-1c").split(".")[0])
    
    def get_line_text(self, line_number: int) -> str:
        """指定された行のテキストを取得する
        
        Args:
            line_number: 行番号（1から始まる）
            
        Returns:
            行のテキスト
        """
        start_index = f"{line_number}.0"
        end_index = f"{line_number}.end"
        return self._textbox.get(start_index, end_index)
