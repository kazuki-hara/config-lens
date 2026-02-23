"""IgnorePatternManager のテスト。"""

import json
from pathlib import Path

import pytest

from src.compare.ignore import IgnorePatternManager
from src.compare.settings import AppSettings


@pytest.fixture
def tmp_settings(tmp_path: Path) -> AppSettings:
    """一時ディレクトリを使用する AppSettings インスタンスを返す。"""
    # モジュールレベルの定数を一時パスで置き換えて使用する
    import src.compare.settings as settings_module

    original_dir = settings_module._SETTINGS_DIR
    original_file = settings_module._SETTINGS_FILE
    try:
        settings_module._SETTINGS_DIR = tmp_path
        settings_module._SETTINGS_FILE = tmp_path / "settings.json"
        yield AppSettings()
    finally:
        settings_module._SETTINGS_DIR = original_dir
        settings_module._SETTINGS_FILE = original_file


@pytest.fixture
def manager(tmp_settings: AppSettings) -> IgnorePatternManager:
    """テスト用の IgnorePatternManager インスタンスを返す。"""
    return IgnorePatternManager(tmp_settings)


class TestIgnorePatternManagerPatternOps:
    """パターンの追加・取得・削除のテスト。"""

    def test_initial_state_is_empty(self, manager: IgnorePatternManager):
        """初期状態でパターンが空であること。"""
        assert manager.get_patterns() == []

    def test_add_pattern(self, manager: IgnorePatternManager):
        """パターンを追加できること。"""
        manager.add_pattern("^!.*")
        assert manager.get_patterns() == ["^!.*"]

    def test_add_multiple_patterns(self, manager: IgnorePatternManager):
        """複数のパターンを順序を維持して追加できること。"""
        manager.add_pattern("^!.*")
        manager.add_pattern("^Building.*")
        assert manager.get_patterns() == ["^!.*", "^Building.*"]

    def test_add_empty_pattern_raises(self, manager: IgnorePatternManager):
        """空文字列を追加しようとすると ValueError が発生すること。"""
        with pytest.raises(ValueError, match="空"):
            manager.add_pattern("")

    def test_add_whitespace_only_pattern_raises(
        self, manager: IgnorePatternManager
    ):
        """空白のみのパターンを追加しようとすると ValueError が発生すること。"""
        with pytest.raises(ValueError, match="空"):
            manager.add_pattern("   ")

    def test_add_duplicate_pattern_raises(self, manager: IgnorePatternManager):
        """重複パターンを追加しようとすると ValueError が発生すること。"""
        manager.add_pattern("^!.*")
        with pytest.raises(ValueError, match="既に登録"):
            manager.add_pattern("^!.*")

    def test_add_invalid_regex_raises(self, manager: IgnorePatternManager):
        """無効な正規表現を追加しようとすると re.error が発生すること。"""
        import re

        with pytest.raises(re.error):
            manager.add_pattern("[invalid")

    def test_remove_pattern(self, manager: IgnorePatternManager):
        """パターンを削除できること。"""
        manager.add_pattern("^!.*")
        manager.add_pattern("^Building.*")
        manager.remove_pattern("^!.*")
        assert manager.get_patterns() == ["^Building.*"]

    def test_remove_nonexistent_pattern(self, manager: IgnorePatternManager):
        """存在しないパターンの削除はエラーにならないこと。"""
        manager.remove_pattern("存在しない")  # 例外が発生しないこと

    def test_get_patterns_returns_copy(self, manager: IgnorePatternManager):
        """get_patterns はコピーを返すこと（内部状態を変更しない）。"""
        manager.add_pattern("^!.*")
        patterns = manager.get_patterns()
        patterns.append("改ざん")
        assert manager.get_patterns() == ["^!.*"]


class TestIgnorePatternManagerMatching:
    """matches メソッドのテスト。"""

    def test_matches_registered_pattern(self, manager: IgnorePatternManager):
        """登録パターンにマッチする行で True を返すこと。"""
        manager.add_pattern("^!")
        assert manager.matches("! コメント行") is True

    def test_does_not_match_without_patterns(
        self, manager: IgnorePatternManager
    ):
        """パターンが未登録の場合、常に False を返すこと。"""
        assert manager.matches("interface GigabitEthernet0/0") is False

    def test_does_not_match_non_matching_line(
        self, manager: IgnorePatternManager
    ):
        """マッチしない行で False を返すこと。"""
        manager.add_pattern("^!")
        assert manager.matches("interface GigabitEthernet0/0") is False

    def test_matches_any_pattern(self, manager: IgnorePatternManager):
        """複数パターンのいずれかにマッチすれば True を返すこと。"""
        manager.add_pattern("^!")
        manager.add_pattern("^Building")
        assert manager.matches("Building configuration...") is True

    def test_partial_match(self, manager: IgnorePatternManager):
        """パターンが行の途中にマッチしても True を返すこと。"""
        manager.add_pattern("NTP")
        assert manager.matches("ntp server 10.0.0.1") is False  # 大文字小文字区別
        assert manager.matches("NTP server 10.0.0.1") is True


class TestIgnorePatternManagerPersistence:
    """設定の永続化テスト。"""

    def test_patterns_saved_to_json(
        self, tmp_settings: AppSettings, tmp_path: Path
    ):
        """パターンが settings.json に保存されること。"""
        manager = IgnorePatternManager(tmp_settings)
        manager.add_pattern("^!.*")

        settings_file = tmp_path / "settings.json"
        assert settings_file.exists()
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        assert data["compare"]["ignore"]["patterns"] == ["^!.*"]

    def test_patterns_loaded_from_json(
        self, tmp_settings: AppSettings, tmp_path: Path
    ):
        """settings.json のパターンが起動時に読み込まれること。"""
        # 事前にJSONを書き込む
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            json.dumps(
                {"compare": {"ignore": {"patterns": ["^!.*", "^Building.*"]}}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        # 新しい AppSettings と IgnorePatternManager でロード
        import src.compare.settings as settings_module

        original_file = settings_module._SETTINGS_FILE
        try:
            settings_module._SETTINGS_FILE = settings_file
            fresh_settings = AppSettings()
            fresh_manager = IgnorePatternManager(fresh_settings)
            assert fresh_manager.get_patterns() == ["^!.*", "^Building.*"]
        finally:
            settings_module._SETTINGS_FILE = original_file

    def test_invalid_json_starts_empty(
        self, tmp_path: Path
    ):
        """壊れた settings.json がある場合、空の状態で起動すること。"""
        import src.compare.settings as settings_module

        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{ invalid json }", encoding="utf-8")

        original_file = settings_module._SETTINGS_FILE
        try:
            settings_module._SETTINGS_FILE = settings_file
            settings = AppSettings()
            manager = IgnorePatternManager(settings)
            assert manager.get_patterns() == []
        finally:
            settings_module._SETTINGS_FILE = original_file

    def test_other_sections_preserved_after_save(
        self, tmp_settings: AppSettings, tmp_path: Path
    ):
        """他機能のセクションが ignore パターン保存/削除後も保持されること。"""
        settings_file = tmp_path / "settings.json"
        # 他機能の設定を事前に書き込む
        settings_file.write_text(
            json.dumps(
                {"other_feature": {"key": "value"}}, ensure_ascii=False
            ),
            encoding="utf-8",
        )

        import src.compare.settings as settings_module

        original_file = settings_module._SETTINGS_FILE
        try:
            settings_module._SETTINGS_FILE = settings_file
            fresh_settings = AppSettings()
            manager = IgnorePatternManager(fresh_settings)
            manager.add_pattern("^!.*")

            data = json.loads(settings_file.read_text(encoding="utf-8"))
            # ignore パターンが保存されていること
            assert data["compare"]["ignore"]["patterns"] == ["^!.*"]
            # 他機能のセクションが消えていないこと
            assert data["other_feature"]["key"] == "value"
        finally:
            settings_module._SETTINGS_FILE = original_file
