"""Config差分分析サービス - 改良版

このモジュールは、ネットワーク機器の設定ファイルの差分を分析し、
変更箇所を特定する機能を提供します。
"""

from dataclasses import dataclass
from hier_config import HConfig, get_hconfig
from enum import Enum

from src.services.cisco_config import CiscoConfigService

class DiffType(Enum):
    """差分の種類を表す列挙型
    
    Attributes:
        ADDED: 追加された行
        REMOVED: 削除された行
        UNCHANGED: 変更されなかった行
    """
    ADDED = "added"
    REMOVED = "removed"
    UNCHANGED = "unchanged"

@dataclass
class DiffLine:
    """差分行を保持するデータクラス
    
    Attributes:
        diff_type: 差分の種類 (追加・削除・変更なし)
        content: +/-を除外した文字列（インデント維持）
        original: 元の文字列
    """
    diff_type: DiffType
    content: str
    original: str

@dataclass
class DiffResult:
    """差分分析結果を保持するデータクラス
    
    Attributes:
        config_a: 比較元のHConfigオブジェクト
        config_b: 比較先のHConfigオブジェクト
        input_config: 投入するHConfigオブジェクト
        line_mapping: 投入configの行番号 -> 比較元・比較先running-configの行番号のマッピング
    """
    config_a: HConfig
    config_b: HConfig
    input_config: HConfig
    line_mapping_config_a: dict[int, int]


class DiffAnalyzer:
    """Config差分分析クラス
    
    HConfigオブジェクトを使用して、設定ファイルの差分を分析します。
    """
    def analyze_diff(
        self,
        current_config: list[str] | HConfig,
        future_config: list[str] | HConfig,
        input_config: list[str] | HConfig,
    ):
        """現在のconfigと将来のconfigの差分を分析し、投入configとの行番号マッピングを取得する

        Args:
            config_a (list[str] | HConfig): _description_
            config_b (list[str] | HConfig): _description_
            input_config (list[str] | HConfig): _description_

        Returns:
            _type_: _description_
        """
        if isinstance(current_config, list):
            current_config_hconfig = get_hconfig("\n".join(current_config))
        elif isinstance(current_config, HConfig):
            current_config_hconfig = current_config
        if isinstance(future_config, list):
            future_config_hconfig = get_hconfig("\n".join(future_config))
        elif isinstance(future_config, HConfig):
            future_config_hconfig = future_config
        diff_lines = DiffAnalyzer.get_diff_lines(current_config_hconfig, future_config_hconfig)

        diff_lines_path = CiscoConfigService.get_config_paths(diff_lines)


        


    @staticmethod
    def get_diff_lines(
        current_config: HConfig,
        future_config: HConfig
    )-> list[DiffLine]:
        """2つの設定の差分を分析する
        
        Args:
            current_config: 現在の設定
            future_config: 将来の設定（想定される設定）
            
        Returns:
            list[DiffLine]: 差分分析結果
        """
        config_diff = CiscoConfigService.get_config_diff(current_config, future_config)
        diff_lines: list[DiffLine] = []
        for line in config_diff:
            diff_line = DiffAnalyzer.parse_diff_line(line)
            diff_lines.append(diff_line)
        return diff_lines

    @staticmethod
    def parse_diff_line(line: str) -> DiffLine:
        """差分行を解析してDiffLineオブジェクトを作成する
        
        Args:
            line: 差分行の文字列
            
        Returns:
            DiffLine: 解析結果のDiffLineオブジェクト
        """
        striped_line = line.lstrip()
        indent = line[:len(line) - len(striped_line)]
        if striped_line.startswith("+"):
            diff_type = DiffType.ADDED
            content = indent + striped_line[2:]
        elif striped_line.startswith("-"):
            diff_type = DiffType.REMOVED
            content = indent + striped_line[2:]
        else:
            diff_type = DiffType.UNCHANGED
            content = line
        return DiffLine(diff_type=diff_type, content=content, original=line)
    
    @staticmethod
    def mapping_line_numbers(config_line: list[str] | HConfig, map_list: list[str] | HConfig) -> dict[int, int]:
        """設定テキストの行番号マッピングを作成する
        
        Args:
            config_line: running-configの行ごとのリスト
            map_list: マッピング対象のリスト
            
        Returns:
            dict[int, int]: 行番号マッピング
        """
        line_mapping: dict[int, int] = {}
        config_path_list = CiscoConfigService.get_config_paths(config_line)
        map_list_path_list = CiscoConfigService.get_config_paths(map_list)
        for i, line in enumerate(map_list_path_list):
            for j, config in enumerate(config_path_list):
                if line == config:
                    line_mapping[i] = j
                    break
        return line_mapping



