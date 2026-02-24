"""Config Validator ロジック（validate/logic.py）のテスト。

単体テスト:
  - ValidateResult データクラスのデフォルト値
  - _build_change_key_maps() の照合キー構築ロジック
  - validate() の差分ラベリング（change_remove / remove / change_add / add）

結合テスト:
  - eBGP 構成変更シナリオ（tests/fixtures/eBGP/ を使用）
  - VLAN 構成変更シナリオ（tests/fixtures/vlan/ を使用）
"""

from pathlib import Path

import pytest
from hier_config import Platform

from src.validate.logic import ValidateResult, _build_change_key_maps, validate


# ---------------------------------------------------------------------------
# ValidateResult データクラスのテスト
# ---------------------------------------------------------------------------


class TestValidateResult:
    """ValidateResult のデータクラス特性をテストする。"""

    def test_default_is_valid_true(self) -> None:
        """is_valid のデフォルトが True であること。"""
        result = ValidateResult(
            running_lines=[],
            expected_lines=[],
            change_lines=[],
            running_types=[],
            expected_types=[],
            change_types=[],
        )
        assert result.is_valid is True

    def test_default_has_unapplied_change_false(self) -> None:
        """has_unapplied_change のデフォルトが False であること。"""
        result = ValidateResult(
            running_lines=[],
            expected_lines=[],
            change_lines=[],
            running_types=[],
            expected_types=[],
            change_types=[],
        )
        assert result.has_unapplied_change is False

    def test_default_mapping_dicts_are_empty(self) -> None:
        """change_to_running / change_to_expected のデフォルトが空辞書であること。"""
        result = ValidateResult(
            running_lines=[],
            expected_lines=[],
            change_lines=[],
            running_types=[],
            expected_types=[],
            change_types=[],
        )
        assert result.change_to_running == {}
        assert result.change_to_expected == {}

    def test_mutable_default_does_not_share_state(self) -> None:
        """複数インスタンス間でデフォルト辞書が共有されないこと（field(default_factory)）。"""
        r1 = ValidateResult(
            running_lines=[], expected_lines=[], change_lines=[],
            running_types=[], expected_types=[], change_types=[],
        )
        r2 = ValidateResult(
            running_lines=[], expected_lines=[], change_lines=[],
            running_types=[], expected_types=[], change_types=[],
        )
        r1.change_to_running[0] = [1]
        assert 0 not in r2.change_to_running


# ---------------------------------------------------------------------------
# _build_change_key_maps() の単体テスト
# ---------------------------------------------------------------------------


class TestBuildChangeKeyMaps:
    """_build_change_key_maps() のキー生成ロジックを検証する。"""

    def test_no_command_registers_to_remove_key_map(self) -> None:
        """'no X' 行は remove_key_map に 'X' として登録されること。"""
        lines = ["no interface FastEthernet0/0"]
        _, remove_key_map = _build_change_key_maps(lines)
        assert "interface FastEthernet0/0" in remove_key_map

    def test_no_command_registers_to_add_key_map(self) -> None:
        """'no X' 行は add_key_map に 'no X' として登録されること。"""
        lines = ["no interface FastEthernet0/0"]
        add_key_map, _ = _build_change_key_maps(lines)
        assert "no interface FastEthernet0/0" in add_key_map

    def test_normal_command_registers_to_add_key_map(self) -> None:
        """通常行は add_key_map にそのまま登録されること。"""
        lines = ["interface FastEthernet0/0"]
        add_key_map, _ = _build_change_key_maps(lines)
        assert "interface FastEthernet0/0" in add_key_map

    def test_normal_command_registers_no_form_to_remove_key_map(self) -> None:
        """通常行は remove_key_map に 'no X' として登録されること。"""
        lines = ["interface FastEthernet0/0"]
        _, remove_key_map = _build_change_key_maps(lines)
        assert "no interface FastEthernet0/0" in remove_key_map

    def test_blank_lines_are_skipped(self) -> None:
        """空行は両マップに登録されないこと。"""
        lines = ["", "   "]
        add_key_map, remove_key_map = _build_change_key_maps(lines)
        assert len(add_key_map) == 0
        assert len(remove_key_map) == 0

    def test_comment_lines_are_skipped(self) -> None:
        """'!' 行は両マップに登録されないこと。"""
        lines = ["!"]
        add_key_map, remove_key_map = _build_change_key_maps(lines)
        assert len(add_key_map) == 0
        assert len(remove_key_map) == 0

    def test_hierarchical_key_uses_parent_path(self) -> None:
        """子行のキーには親行のパスが含まれること。"""
        lines = [
            "router bgp 100",
            " neighbor 10.0.1.2 remote-as 200",
        ]
        add_key_map, _ = _build_change_key_maps(lines)
        expected_key = "router bgp 100 > neighbor 10.0.1.2 remote-as 200"
        assert expected_key in add_key_map

    def test_multiple_lines_register_correct_indices(self) -> None:
        """複数行のインデックスが正しくマップされること。"""
        lines = [
            "interface FastEthernet0/0",
            "interface FastEthernet0/1",
        ]
        add_key_map, _ = _build_change_key_maps(lines)
        # 各 key → インデックス 0, 1 が登録されている
        assert add_key_map["interface FastEthernet0/0"] == [0]
        assert add_key_map["interface FastEthernet0/1"] == [1]


# ---------------------------------------------------------------------------
# validate() の単体テスト
# ---------------------------------------------------------------------------


class TestValidateIdentical:
    """running == expected の場合（差分なし）のテスト。"""

    def test_no_remove_or_add_types(self) -> None:
        """差分がなければ running_types に remove/add が含まれないこと。"""
        config = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            " no shutdown\n"
            "!"
        )
        result = validate(config, "", config, Platform.CISCO_IOS)

        assert "remove" not in result.running_types
        assert "add" not in result.expected_types

    def test_is_valid_true(self) -> None:
        """差分がなければ is_valid が True であること。"""
        config = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            "!"
        )
        result = validate(config, "", config, Platform.CISCO_IOS)
        assert result.is_valid is True

    def test_line_list_lengths_are_equal(self) -> None:
        """running_lines と expected_lines の長さが常に等しいこと。"""
        config = "interface GigabitEthernet0/0\n ip address 192.168.1.1 255.255.255.0\n!"
        result = validate(config, "", config, Platform.CISCO_IOS)
        assert len(result.running_lines) == len(result.expected_lines)


class TestValidateDelete:
    """running にのみ存在するブロック（削除差分）のテスト。"""

    def test_change_covered_delete_becomes_change_remove(self) -> None:
        """change が no コマンドで説明できる削除は change_remove になること。"""
        running = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            " no shutdown\n"
            "!"
        )
        change = "no interface GigabitEthernet0/0\n!"
        expected = "!"

        result = validate(running, change, expected, Platform.CISCO_IOS)

        assert "change_remove" in result.running_types
        assert "remove" not in result.running_types

    def test_change_covered_delete_is_valid(self) -> None:
        """change で説明できる削除のみなら is_valid が True であること。"""
        running = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            "!"
        )
        change = "no interface GigabitEthernet0/0\n!"
        expected = "!"

        result = validate(running, change, expected, Platform.CISCO_IOS)
        assert result.is_valid is True

    def test_uncovered_delete_becomes_remove(self) -> None:
        """change で説明できない削除は remove になること。"""
        running = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            "!"
        )
        expected = "!"

        result = validate(running, "", expected, Platform.CISCO_IOS)

        assert "remove" in result.running_types

    def test_uncovered_delete_is_invalid(self) -> None:
        """change で説明できない削除があれば is_valid が False であること。"""
        running = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            "!"
        )
        expected = "!"

        result = validate(running, "", expected, Platform.CISCO_IOS)
        assert result.is_valid is False

    def test_change_to_running_mapping_populated_on_covered_delete(self) -> None:
        """change_remove 行には change_to_running マッピングが存在すること。"""
        running = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            "!"
        )
        change = "no interface GigabitEthernet0/0\n!"
        expected = "!"

        result = validate(running, change, expected, Platform.CISCO_IOS)
        assert len(result.change_to_running) > 0

    def test_change_lines_length_matches_input(self) -> None:
        """change_lines は change_text の行数と一致すること。"""
        running = "interface GigabitEthernet0/0\n ip address 192.168.1.1 255.255.255.0\n!"
        change = "no interface GigabitEthernet0/0\n!"
        expected = "!"

        result = validate(running, change, expected, Platform.CISCO_IOS)
        assert len(result.change_lines) == len(change.splitlines())


class TestValidateInsert:
    """expected にのみ存在するブロック（追加差分）のテスト。"""

    def test_change_covered_insert_becomes_change_add(self) -> None:
        """change が追加コマンドで説明できる挿入は change_add になること。"""
        running = "!"
        change = (
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )
        expected = (
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )

        result = validate(running, change, expected, Platform.CISCO_IOS)

        assert "change_add" in result.expected_types
        assert "add" not in result.expected_types

    def test_change_covered_insert_is_valid(self) -> None:
        """change で説明できる追加のみなら is_valid が True であること。"""
        running = "!"
        change = (
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )
        expected = (
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )

        result = validate(running, change, expected, Platform.CISCO_IOS)
        assert result.is_valid is True

    def test_uncovered_insert_becomes_add(self) -> None:
        """change で説明できない追加は add になること。"""
        running = "!"
        expected = (
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )

        result = validate(running, "", expected, Platform.CISCO_IOS)

        assert "add" in result.expected_types

    def test_uncovered_insert_is_invalid(self) -> None:
        """change で説明できない追加があれば is_valid が False であること。"""
        running = "!"
        expected = (
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )

        result = validate(running, "", expected, Platform.CISCO_IOS)
        assert result.is_valid is False

    def test_change_to_expected_mapping_populated_on_covered_insert(self) -> None:
        """change_add 行には change_to_expected マッピングが存在すること。"""
        running = "!"
        change = (
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )
        expected = (
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )

        result = validate(running, change, expected, Platform.CISCO_IOS)
        assert len(result.change_to_expected) > 0


class TestValidateUnmatched:
    """change に記述があるが差分に現れない行（unmatched）のテスト。"""

    def test_change_not_reflected_in_diff_is_unmatched(self) -> None:
        """change に記述があるが running/expected に差分として現れない行は
        unmatched になること。"""
        # running/expected は同一 → 差分なし
        config = "interface GigabitEthernet0/0\n ip address 192.168.1.1 255.255.255.0\n!"
        # change には設定追加が書かれているが expected に反映されていない
        change = "interface GigabitEthernet0/1\n no shutdown\n!"

        result = validate(config, change, config, Platform.CISCO_IOS)

        assert "unmatched" in result.change_types
        assert result.has_unapplied_change is True

    def test_fully_matched_change_has_no_unmatched(self) -> None:
        """全 change 行が差分に対応していれば unmatched が存在しないこと。"""
        running = "!"
        change = "interface GigabitEthernet0/1\n no shutdown\n!"
        expected = "interface GigabitEthernet0/1\n no shutdown\n!"

        result = validate(running, change, expected, Platform.CISCO_IOS)

        assert "unmatched" not in result.change_types
        assert result.has_unapplied_change is False


class TestValidateResultStructure:
    """ValidateResult の構造的整合性テスト。"""

    def test_running_types_length_matches_running_lines(self) -> None:
        """running_types の長さが running_lines と一致すること。"""
        running = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            "!"
        )
        expected = "!"
        change = "no interface GigabitEthernet0/0\n!"

        result = validate(running, change, expected, Platform.CISCO_IOS)

        assert len(result.running_types) == len(result.running_lines)

    def test_expected_types_length_matches_expected_lines(self) -> None:
        """expected_types の長さが expected_lines と一致すること。"""
        running = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            "!"
        )
        expected = "!"
        change = "no interface GigabitEthernet0/0\n!"

        result = validate(running, change, expected, Platform.CISCO_IOS)

        assert len(result.expected_types) == len(result.expected_lines)

    def test_change_types_length_matches_change_lines(self) -> None:
        """change_types の長さが change_lines と一致すること。"""
        running = "!"
        change = "interface GigabitEthernet0/1\n no shutdown\n!"
        expected = "interface GigabitEthernet0/1\n no shutdown\n!"

        result = validate(running, change, expected, Platform.CISCO_IOS)

        assert len(result.change_types) == len(result.change_lines)

    def test_all_running_types_are_valid_strings(self) -> None:
        """running_types の各値が想定された文字列であること。"""
        valid_types = {"equal", "change_remove", "remove", "reorder", "empty"}
        running = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            "!"
        )
        expected = "interface GigabitEthernet0/1\n ip address 10.0.0.1 255.255.255.0\n!"
        change = (
            "no interface GigabitEthernet0/0\n"
            "interface GigabitEthernet0/1\n"
            " ip address 10.0.0.1 255.255.255.0\n"
            "!"
        )

        result = validate(running, change, expected, Platform.CISCO_IOS)

        for t in result.running_types:
            assert t in valid_types, f"想定外の running_type: {t}"

    def test_all_expected_types_are_valid_strings(self) -> None:
        """expected_types の各値が想定された文字列であること。"""
        valid_types = {"equal", "change_add", "add", "reorder", "empty"}
        running = "interface GigabitEthernet0/0\n ip address 192.168.1.1 255.255.255.0\n!"
        expected = "interface GigabitEthernet0/1\n ip address 10.0.0.1 255.255.255.0\n!"
        change = (
            "no interface GigabitEthernet0/0\n"
            "interface GigabitEthernet0/1\n"
            " ip address 10.0.0.1 255.255.255.0\n"
            "!"
        )

        result = validate(running, change, expected, Platform.CISCO_IOS)

        for t in result.expected_types:
            assert t in valid_types, f"想定外の expected_type: {t}"

    def test_all_change_types_are_valid_strings(self) -> None:
        """change_types の各値が想定された文字列であること。"""
        valid_types = {"normal", "change", "unmatched"}
        running = "!"
        change = "interface GigabitEthernet0/1\n no shutdown\n!"
        expected = "interface GigabitEthernet0/1\n no shutdown\n!"

        result = validate(running, change, expected, Platform.CISCO_IOS)

        for t in result.change_types:
            assert t in valid_types, f"想定外の change_type: {t}"


# ---------------------------------------------------------------------------
# 結合テスト: eBGP シナリオ（tests/fixtures/eBGP/ を使用）
# ---------------------------------------------------------------------------


FIXTURE_EBGP_DIR = Path("tests/fixtures/eBGP")


@pytest.fixture
def ebgp_running() -> str:
    """eBGP シナリオ: 現在の running-config（current.txt）。"""
    return FIXTURE_EBGP_DIR.joinpath("current.txt").read_text(encoding="utf-8")


@pytest.fixture
def ebgp_change() -> str:
    """eBGP シナリオ: 設定変更内容（input.txt）。"""
    return FIXTURE_EBGP_DIR.joinpath("input.txt").read_text(encoding="utf-8")


@pytest.fixture
def ebgp_expected() -> str:
    """eBGP シナリオ: 想定される running-config（after.txt）。"""
    return FIXTURE_EBGP_DIR.joinpath("after.txt").read_text(encoding="utf-8")


class TestValidateEBGPIntegration:
    """eBGP 構成変更シナリオの結合テスト。

    tests/fixtures/eBGP/ の実際のコンフィグファイルを使用して
    validate() の動作を検証する。
    """

    def test_line_list_lengths_are_equal(
        self, ebgp_running: str, ebgp_change: str, ebgp_expected: str
    ) -> None:
        """running_lines と expected_lines の長さが等しいこと。"""
        result = validate(ebgp_running, ebgp_change, ebgp_expected, Platform.CISCO_IOS)
        assert len(result.running_lines) == len(result.expected_lines)

    def test_type_list_lengths_match_line_lists(
        self, ebgp_running: str, ebgp_change: str, ebgp_expected: str
    ) -> None:
        """各 types リストの長さが対応する lines リストと一致すること。"""
        result = validate(ebgp_running, ebgp_change, ebgp_expected, Platform.CISCO_IOS)
        assert len(result.running_types) == len(result.running_lines)
        assert len(result.expected_types) == len(result.expected_lines)
        assert len(result.change_types) == len(result.change_lines)

    def test_change_lines_match_input_text(
        self, ebgp_running: str, ebgp_change: str, ebgp_expected: str
    ) -> None:
        """change_lines が入力テキストの行数と一致すること。"""
        result = validate(ebgp_running, ebgp_change, ebgp_expected, Platform.CISCO_IOS)
        assert len(result.change_lines) == len(ebgp_change.splitlines())

    def test_no_interface_removal_is_classified(
        self, ebgp_running: str, ebgp_change: str, ebgp_expected: str
    ) -> None:
        """'no interface FastEthernet0/0.2' による削除が
        change_remove または remove として分類されること。"""
        result = validate(ebgp_running, ebgp_change, ebgp_expected, Platform.CISCO_IOS)
        # FastEthernet0/0.2 の行が running_types に現れているか確認
        has_delete_type = any(
            t in ("change_remove", "remove") for t in result.running_types
        )
        assert has_delete_type

    def test_new_interface_addition_is_classified(
        self, ebgp_running: str, ebgp_change: str, ebgp_expected: str
    ) -> None:
        """FastEthernet0/0.1 の追加が change_add または add として
        分類されること。"""
        result = validate(ebgp_running, ebgp_change, ebgp_expected, Platform.CISCO_IOS)
        has_add_type = any(
            t in ("change_add", "add") for t in result.expected_types
        )
        assert has_add_type

    def test_running_types_only_contain_valid_values(
        self, ebgp_running: str, ebgp_change: str, ebgp_expected: str
    ) -> None:
        """running_types の全値が想定文字列のみであること。"""
        valid = {"equal", "change_remove", "remove", "reorder", "empty"}
        result = validate(ebgp_running, ebgp_change, ebgp_expected, Platform.CISCO_IOS)
        unexpected = {t for t in result.running_types if t not in valid}
        assert not unexpected, f"想定外の running_type: {unexpected}"

    def test_expected_types_only_contain_valid_values(
        self, ebgp_running: str, ebgp_change: str, ebgp_expected: str
    ) -> None:
        """expected_types の全値が想定文字列のみであること。"""
        valid = {"equal", "change_add", "add", "reorder", "empty"}
        result = validate(ebgp_running, ebgp_change, ebgp_expected, Platform.CISCO_IOS)
        unexpected = {t for t in result.expected_types if t not in valid}
        assert not unexpected, f"想定外の expected_type: {unexpected}"

    def test_change_types_only_contain_valid_values(
        self, ebgp_running: str, ebgp_change: str, ebgp_expected: str
    ) -> None:
        """change_types の全値が想定文字列のみであること。"""
        valid = {"normal", "change", "unmatched"}
        result = validate(ebgp_running, ebgp_change, ebgp_expected, Platform.CISCO_IOS)
        unexpected = {t for t in result.change_types if t not in valid}
        assert not unexpected, f"想定外の change_type: {unexpected}"
