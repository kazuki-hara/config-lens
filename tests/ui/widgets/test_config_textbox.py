"""ConfigTextboxウィジェットのテスト"""

import pytest
from src.ui.widgets.config_textbox import ConfigTextbox, HighlightStyle


class TestHighlightStyle:
    """HighlightStyleデータクラスのテスト"""
    
    def test_highlight_style_creation(self) -> None:
        """HighlightStyleが正しく作成されることを確認する"""
        style = HighlightStyle(
            background="#FFE066",
            foreground="black",
            font_weight="bold"
        )
        
        assert style.background == "#FFE066"
        assert style.foreground == "black"
        assert style.font_weight == "bold"
    
    def test_highlight_style_default_font_weight(self) -> None:
        """font_weightのデフォルト値が正しいことを確認する"""
        style = HighlightStyle(
            background="#FFE066",
            foreground="black"
        )
        
        assert style.font_weight == "normal"


class TestConfigTextbox:
    """ConfigTextboxウィジェットのテスト"""
    
    @pytest.fixture
    def textbox(self) -> ConfigTextbox:
        """テスト用のConfigTextboxインスタンスを作成する
        
        Note:
            tkinterウィジェットは実際のGUI環境が必要なため、
            このテストはヘッドレス環境では失敗する可能性がある。
            CI環境では適切な設定が必要。
        """
        import tkinter as tk
        root = tk.Tk()
        textbox = ConfigTextbox(master=root)
        yield textbox
        root.destroy()
    
    def test_default_styles_initialized(self, textbox: ConfigTextbox) -> None:
        """デフォルトスタイルが初期化されることを確認する"""
        available_styles = textbox.get_available_styles()
        
        assert "default" in available_styles
        assert "add" in available_styles
        assert "remove" in available_styles
        assert "modify" in available_styles
    
    def test_set_text(self, textbox: ConfigTextbox) -> None:
        """テキストが正しく設定されることを確認する"""
        test_text = "line 1\nline 2\nline 3"
        textbox.set_text(test_text, readonly=False)
        
        content = textbox.get("1.0", "end-1c")
        assert content == test_text
    
    def test_set_text_readonly(self, textbox: ConfigTextbox) -> None:
        """読み取り専用モードが正しく設定されることを確認する"""
        test_text = "test content"
        textbox.set_text(test_text, readonly=True)
        
        # 読み取り専用になっていることを確認（内部の_textbox経由）
        state = str(textbox._textbox.cget("state"))
        assert state == "disabled"
    
    def test_add_highlight_style(self, textbox: ConfigTextbox) -> None:
        """カスタムハイライトスタイルが追加できることを確認する"""
        custom_style = HighlightStyle(
            background="#FF0000",
            foreground="white",
            font_weight="bold"
        )
        
        textbox.add_highlight_style("custom", custom_style)
        
        assert "custom" in textbox.get_available_styles()
    
    def test_highlight_lines(self, textbox: ConfigTextbox) -> None:
        """行がハイライトされることを確認する"""
        test_text = "line 1\nline 2\nline 3\nline 4\nline 5"
        textbox.set_text(test_text, readonly=False)
        
        # 2行目と4行目をハイライト
        textbox.highlight_lines([2, 4], style_name="default")
        
        # タグが正しく適用されているか確認（内部の_textbox経由）
        tags_line_2 = textbox._textbox.tag_names("2.0")
        assert "default" in tags_line_2
        
        tags_line_4 = textbox._textbox.tag_names("4.0")
        assert "default" in tags_line_4
        tags_line_4 = textbox._textbox.tag_names("4.0")
        assert "default" in tags_line_4
    
    def test_highlight_lines_invalid_style(self, textbox: ConfigTextbox) -> None:
        """存在しないスタイルでエラーが発生することを確認する"""
        test_text = "line 1\nline 2"
        textbox.set_text(test_text, readonly=False)
        
        with pytest.raises(ValueError, match="スタイル .* が見つかりません"):
            textbox.highlight_lines([1], style_name="nonexistent")
    
    def test_clear_highlights_all(self, textbox: ConfigTextbox) -> None:
        """すべてのハイライトがクリアされることを確認する"""
        test_text = "line 1\nline 2\nline 3"
        textbox.set_text(test_text, readonly=False)
        
        # 複数のスタイルでハイライト
        textbox.highlight_lines([1], style_name="add")
        textbox.highlight_lines([2], style_name="remove")
        
        # すべてクリア
        textbox.clear_highlights()
        
        # タグが削除されていることを確認（内部の_textbox経由）
        tags_line_1 = textbox._textbox.tag_names("1.0")
        assert "add" not in tags_line_1
        
        tags_line_2 = textbox._textbox.tag_names("2.0")
        assert "remove" not in tags_line_2
    
    def test_clear_highlights_specific(self, textbox: ConfigTextbox) -> None:
        """特定のハイライトだけがクリアされることを確認する"""
        test_text = "line 1\nline 2"
        textbox.set_text(test_text, readonly=False)
        
        # 2つのスタイルでハイライト
        textbox.highlight_lines([1], style_name="add")
        textbox.highlight_lines([1], style_name="remove")
        
        # addだけクリア
        textbox.clear_highlights(style_name="add")
        
        # addタグは削除され、removeタグは残っていることを確認（内部の_textbox経由）
        tags = textbox._textbox.tag_names("1.0")
        assert "add" not in tags
        assert "remove" in tags
    
    def test_highlight_lines_works_with_readonly(
        self, textbox: ConfigTextbox
    ) -> None:
        """読み取り専用状態でもハイライトできることを確認する"""
        test_text = "line 1\nline 2\nline 3"
        textbox.set_text(test_text, readonly=True)
        
        # 読み取り専用でもハイライトできる
        textbox.highlight_lines([2], style_name="default")
        
        # ハイライトが適用されていることを確認（内部の_textbox経由）
        tags = textbox._textbox.tag_names("2.0")
        assert "default" in tags
        
        # 読み取り専用のままであることを確認（内部の_textbox経由）
        state = str(textbox._textbox.cget("state"))
        assert state == "disabled"
