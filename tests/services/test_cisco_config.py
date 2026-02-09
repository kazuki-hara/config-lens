import pytest
from src.services.cisco_config import CiscoConfigService
from pprint import pprint


class TestCiscoConfigService:
    @pytest.fixture
    def cisco_service(self) -> CiscoConfigService:
        return CiscoConfigService()

    def test_platform_property(self, cisco_service: CiscoConfigService) -> None:
        assert cisco_service.platform is not None

    def test_read_config_readlines(self, cisco_service: CiscoConfigService) -> None:
        lines = cisco_service.read_config_readlines(
            "tests/fixtures/cisco_running-config_default.txt"
        )
        assert isinstance(lines, list)
        assert len(lines) > 0

    def test_read_config(self, cisco_service: CiscoConfigService) -> None:
        config = cisco_service.read_config(
            "tests/fixtures/cisco_running-config_default.txt"
        )
        assert config is not None

    def test_get_config_diff(self, cisco_service: CiscoConfigService) -> None:
        config_a = cisco_service.read_config(
            "tests/fixtures/cisco_running-config_default.txt"
        )
        config_b = cisco_service.read_config(
            "tests/fixtures/cisco_running-config_future.txt"
        )
        assert config_a is not None
        assert config_b is not None
        diff = cisco_service.get_config_diff(config_a, config_a)
        assert diff == []
        diff = cisco_service.get_config_diff(config_a, config_b)
        assert isinstance(diff, list)
        assert len(diff) > 0

    def test_get_config_paths(self, cisco_service: CiscoConfigService) -> None:
        config = cisco_service.read_config(
            "tests/fixtures/cisco_add.txt"
        )
        cisco_service.get_config_paths(config)

        config = cisco_service.read_config_readlines(
            "tests/fixtures/cisco_add.txt"
        )
        paths = cisco_service.get_config_paths(config)

        
