"""メインウィンドウ - 3列Config差分表示

現在のrunning-config、投入するconfig、想定されるrunning-configを
3列で並べて表示し、差分をハイライトします。
"""

import customtkinter
from pathlib import Path
from tkinter import filedialog
from hier_config import HConfig
from hier_config.utils import read_text_from_file

from services.cisco_config import CiscoConfigService
from services.diff_analyzer import DiffAnalyzer
from ui.widgets.config_textbox import ConfigTextbox


class MainWindow(customtkinter.CTk):
    """メインウィンドウクラス
    
    3つのconfig表示エリアと差分ハイライト機能を提供します。
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.title("Config Lens - Config差分ビューア")
        self.geometry("1800x900")
        
        # サービスの初期化
        self.cisco_service = CiscoConfigService()
        self.diff_analyzer = DiffAnalyzer()
        
        # Config保持用
        self.current_config: HConfig | None = None
        self.add_config: HConfig | None = None
        self.future_config: HConfig | None = None
        
        # 行番号マッピング
        self.line_mapping: dict[int, list[int]] = {}
        
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """UIコンポーネントを設定する"""
        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")
        
        # グリッドの重みを設定
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        
        # ===== 左列：現在のrunning-config =====
        self.current_button = customtkinter.CTkButton(
            master=self,
            text="現在の running-config を選択",
            command=self.load_current_config,
        )
        self.current_button.grid(
            row=0, column=0, padx=(20, 5), pady=20, sticky="ew"
        )
        
        self.current_label = customtkinter.CTkLabel(
            master=self, text="現在のConfig"
        )
        self.current_label.grid(
            row=0, column=0, padx=(20, 5), pady=(60, 0), sticky="n"
        )
        
        self.current_textbox = ConfigTextbox(
            master=self,
            width=550,
            height=700,
            font=("Courier", 11),
        )
        self.current_textbox.grid(
            row=1, column=0, padx=(20, 5), pady=(0, 20), sticky="nsew"
        )
        
        # ===== 中央列：投入するconfig =====
        self.add_button = customtkinter.CTkButton(
            master=self,
            text="投入する config を選択",
            command=self.load_add_config,
        )
        self.add_button.grid(
            row=0, column=1, padx=5, pady=20, sticky="ew"
        )
        
        self.add_label = customtkinter.CTkLabel(
            master=self, text="投入Config"
        )
        self.add_label.grid(
            row=0, column=1, padx=5, pady=(60, 0), sticky="n"
        )
        
        self.add_textbox = ConfigTextbox(
            master=self,
            width=550,
            height=700,
            font=("Courier", 11),
        )
        self.add_textbox.grid(
            row=1, column=1, padx=5, pady=(0, 20), sticky="nsew"
        )
        
        # クリックイベントを設定
        self.add_textbox.set_line_click_callback(self.on_add_config_click)
        
        # ===== 右列：想定されるrunning-config =====
        self.future_button = customtkinter.CTkButton(
            master=self,
            text="想定 running-config を選択",
            command=self.load_future_config,
        )
        self.future_button.grid(
            row=0, column=2, padx=(5, 20), pady=20, sticky="ew"
        )
        
        self.future_label = customtkinter.CTkLabel(
            master=self, text="想定されるConfig"
        )
        self.future_label.grid(
            row=0, column=2, padx=(5, 20), pady=(60, 0), sticky="n"
        )
        
        self.future_textbox = ConfigTextbox(
            master=self,
            width=550,
            height=700,
            font=("Courier", 11),
        )
        self.future_textbox.grid(
            row=1, column=2, padx=(5, 20), pady=(0, 20), sticky="nsew"
        )
    
    def read_file_path(self) -> Path | None:
        """ファイル選択ダイアログを表示してファイルパスを取得する
        
        Returns:
            選択されたファイルのパス、キャンセルされた場合はNone
        """
        file_path = filedialog.askopenfilename(
            title="Configファイルを選択",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        
        if not file_path:
            return None
        
        return Path(file_path)
    
    def load_current_config(self) -> None:
        """現在のrunning-configファイルを読み込む"""
        file_path = self.read_file_path()
        if not file_path:
            return
        
        # ファイルを読み込み
        config_text = read_text_from_file(str(file_path))
        self.current_config = self.cisco_service.read_config(file_path)
        
        # 表示
        self.current_textbox.set_text(config_text, readonly=True)
        self.current_label.configure(text=f"現在: {file_path.name}")
        
        # 差分があれば再計算
        if self.future_config:
            self.highlight_diff()
    
    def load_add_config(self) -> None:
        """投入するconfigファイルを読み込む"""
        file_path = self.read_file_path()
        if not file_path:
            return
        
        # ファイルを読み込み
        config_text = read_text_from_file(str(file_path))
        self.add_config = self.cisco_service.read_config(file_path)
        
        # 表示
        self.add_textbox.set_text(config_text, readonly=True)
        self.add_label.configure(text=f"投入: {file_path.name}")
        
        # 全行を黄色でハイライト（参照用）
        add_line_count = self.add_textbox.get_line_count()
        if add_line_count > 0:
            all_add_lines = list(range(1, add_line_count + 1))
            self.add_textbox.highlight_lines(all_add_lines, "modify")
        
        # 行番号マッピングを作成
        if self.future_config and self.add_config:
            self.line_mapping = self.diff_analyzer.create_line_mapping(
                self.add_config, self.future_config
            )
    
    def load_future_config(self) -> None:
        """想定されるrunning-configファイルを読み込む"""
        file_path = self.read_file_path()
        if not file_path:
            return
        
        # ファイルを読み込み
        config_text = read_text_from_file(str(file_path))
        self.future_config = self.cisco_service.read_config(file_path)
        
        # 表示
        self.future_textbox.set_text(config_text, readonly=True)
        self.future_label.configure(text=f"想定: {file_path.name}")
        
        # 差分があれば計算
        if self.current_config:
            self.highlight_diff()
        
        # 行番号マッピングを作成
        if self.add_config and self.future_config:
            self.line_mapping = self.diff_analyzer.create_line_mapping(
                self.add_config, self.future_config
            )
    
    def highlight_diff(self) -> None:
        """差分をハイライト表示する"""
        if not self.current_config or not self.future_config:
            return
        
        # 差分を分析
        diff_result = self.diff_analyzer.analyze_diff(
            self.current_config, self.future_config
        )
        
        # 現在のconfigで削除される行を赤でハイライト
        if diff_result.removed_lines:
            self.current_textbox.highlight_lines(
                diff_result.removed_lines, "remove"
            )
        
        # 将来のconfigで追加される行を緑でハイライト
        if diff_result.added_lines:
            self.future_textbox.highlight_lines(
                diff_result.added_lines, "add"
            )
    
    def on_add_config_click(self, line_number: int) -> None:
        """投入configの行がクリックされた時の処理
        
        Args:
            line_number: クリックされた行番号
        """
        # 既存の強調表示をクリア
        self.add_textbox.clear_emphasis()
        self.future_textbox.clear_emphasis()
        
        # 対応する行を取得
        related_lines = self.diff_analyzer.get_related_lines(
            self.line_mapping, line_number
        )
        
        if related_lines:
            # 投入configの行を強調
            self.add_textbox.emphasize_lines([line_number], "default")
            
            # 対応する将来のconfigの行を強調
            self.future_textbox.emphasize_lines(related_lines, "add")
