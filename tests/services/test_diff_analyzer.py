import pytest

from src.services.diff_analyzer import DiffResult, DiffAnalyzer

class TestDiffAnalyzer:
    @pytest.fixture
    def diff_analyzer(self) -> DiffAnalyzer:
        return DiffAnalyzer()
    
    def test_analyze_diff(self, diff_analyzer: DiffAnalyzer) -> None:
        from src.services.cisco_config import CiscoConfigService

        cisco_service = CiscoConfigService()
        config_a = cisco_service.read_config(
            "tests/fixtures/cisco_running-config_default.txt"
        )
        config_b = cisco_service.read_config(
            "tests/fixtures/cisco_running-config_future.txt"
        )
        input_config = cisco_service.read_config(
            "tests/fixtures/cisco_add.txt"
        )
        assert config_a is not None
        assert config_b is not None

        diff_result = diff_analyzer.analyze_diff(config_a, config_b, input_config)

    def test_get_diff_lines(self, diff_analyzer: DiffAnalyzer) -> None:
        from src.services.cisco_config import CiscoConfigService

        cisco_service = CiscoConfigService()
        config_a = cisco_service.read_config(
            "tests/fixtures/cisco_running-config_default.txt"
        )
        config_b = cisco_service.read_config(
            "tests/fixtures/cisco_running-config_future.txt"
        )
        assert config_a is not None
        assert config_b is not None

        diff_result = diff_analyzer.get_diff_lines(config_a, config_b)

    def test_mapping_line_numbers(self, diff_analyzer: DiffAnalyzer) -> None:
        from src.services.cisco_config import CiscoConfigService

        cisco_service = CiscoConfigService()
        future_config_lines = cisco_service.read_config_readlines(
            "tests/fixtures/cisco_running-config_future.txt"
        )
        input_config = cisco_service.read_config(
            "tests/fixtures/cisco_add.txt"
        )

        line_mapping = diff_analyzer.mapping_line_numbers(
            future_config_lines, input_config
        )