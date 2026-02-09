from hier_config import get_hconfig, Platform, HConfig
from hier_config.utils import read_text_from_file
from typing import Optional
from pathlib import Path
from logging import getLogger

logger = getLogger(__name__)
logger.setLevel("DEBUG")


class CiscoConfigService:
    def __init__(self, platform: Platform = Platform.CISCO_IOS) -> None:
        self._platform = platform

    @property
    def platform(self) -> Optional[Platform]:
        return self._platform
    
    @staticmethod
    def read_config_readlines(file_path: str | Path) -> list[str]:
        """テキストファイルを読み込み、行ごとのリストを返す

        Args:
            file_path (str | Path): Configのファイルパス

        Returns:
            list[str]: 行ごとのリスト
        """
        file_path_str = str(file_path)
        config_txt = read_text_from_file(file_path_str)
        config_lines = config_txt.splitlines(keepends=False)
        return config_lines
    
    def read_config(self, file_path: str | Path) -> Optional[HConfig]:
        """テキストファイルを読み込み、HConfigオブジェクトを返す

        Args:
            file_path (str | Path): Configのファイルパス

        Returns:
            Optional[HConfig]: HConfigオブジェクト
        """
        file_path_str = str(file_path)
        config_txt = read_text_from_file(file_path_str)
        if self.platform is None:
            return None
        config = get_hconfig(self.platform, config_txt)
        return config

    @staticmethod
    def get_config_diff(config_a: HConfig, config_b: HConfig) -> list[str]:
        """2つのHConfigオブジェクトの差分を取得する

        Args:
            config_a (HConfig): 比較元のHConfigオブジェクト
            config_b (HConfig): 比較先のHConfigオブジェクト

        Returns:
            list[str]: 差分のリスト
        """
        config_diff_list = list(config_a.unified_diff(config_b))
        return config_diff_list

    def generate_future_config(
        self, current_config: HConfig, input_config: HConfig
    ) -> HConfig:
        """現在の設定と追加する設定から将来の設定を生成する

        Args:
            current_config (HConfig): 現在のHConfigオブジェクト
            input_config (HConfig): 追加するHConfigオブジェクト

        Returns:
            HConfig: 将来のHConfigオブジェクト
        """
        future_config = current_config.future(input_config)
        return future_config
    
    @staticmethod
    def get_config_paths(config: list | HConfig) -> list[list[str]]:
        """
        HConfigオブジェクトから階層パスのリストを取得する。
        
        Args:
            config: HConfigオブジェクトまたは行ごとのリスト
            
        Returns:
            各設定行への完全パスのリスト
            例: [["interface Vlan1"], 
                ["interface Vlan1", " ip address 10.0.0.1 255.255.255.0"],
                ["interface Vlan1", " shutdown"]]
        """
        paths = []

        if isinstance(config, HConfig):
            def traverse(node: HConfig, current_path: list[str]) -> None:
                """
                HConfigツリーを再帰的に走査する。
                
                Args:
                    node: 現在のHConfigノード
                    current_path: 現在のパス
                """
                # 現在のパスを追加
                if current_path:
                    paths.append(current_path.copy())
                
                # 子ノードを走査
                for child in node.children:
                    new_path = current_path + [child.text]
                    traverse(child, new_path)
            
            # ルートレベルの各ノードから走査を開始
            for child in config.children:
                traverse(child, [child.text])
            return paths
        elif isinstance(config, list):
            stack: list[tuple[int, str]] = []  # (インデントレベル, テキスト) のスタック

            for line in config:
                # 改行文字を除去
                line = line.rstrip("\n\r")

                # インデントレベルを計算（先頭のスペース数）
                indent_level = len(line) - len(line.lstrip(" "))

                # 現在の行より深いインデントをスタックから削除
                while stack and stack[-1][0] >= indent_level:
                    stack.pop()

                # 現在のパスを構築
                current_path = [text for _, text in stack] + [line.lstrip()]
                paths.append(current_path)

                # インデントレベル0でない行（子要素）のみスタックに追加
                # インデントレベル0の行は新しいルート要素として扱う
                if indent_level > 0 or (indent_level == 0 and line.strip()):
                    # 空でない行のみスタックに追加
                    if line.strip():
                        stack.append((indent_level, line))
                    # インデントレベル0の場合はスタックをクリア
                    if indent_level == 0:
                        stack = [(indent_level, line)]
            return paths