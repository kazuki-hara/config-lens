from hier_config import get_hconfig, Platform, HConfig
from hier_config.utils import read_text_from_file
from typing import Optional
from pathlib import Path


class CiscoConfigService:
    def __init__(self, platform: Platform = Platform.CISCO_IOS) -> None:
        self._platform = platform

    @property
    def platform(self) -> Optional[Platform]:
        return self._platform

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
        self, current_config: HConfig, add_config: HConfig
    ) -> HConfig:
        """現在の設定と追加する設定から将来の設定を生成する

        Args:
            current_config (HConfig): 現在のHConfigオブジェクト
            add_config (HConfig): 追加するHConfigオブジェクト

        Returns:
            HConfig: 将来のHConfigオブジェクト
        """
        future_config = current_config.merge(add_config)
        return future_config
