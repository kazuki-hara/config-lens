"""比較ロジック（logic.py）のテスト。"""

import pytest
from hier_config import Platform, get_hconfig
from hier_config.utils import read_text_from_file

from src.compare.logic import HierarchicalDiffAnalyzer, TextAlignedDiffComparator


@pytest.fixture
def source_config():
    """テスト用のHConfigオブジェクト（source）。"""
    config_txt = read_text_from_file("tests/fixtures/source.txt")
    return get_hconfig(Platform.CISCO_IOS, config_txt)


@pytest.fixture
def target_config():
    """テスト用のHConfigオブジェクト（target）。"""
    config_txt = read_text_from_file("tests/fixtures/target.txt")
    return get_hconfig(Platform.CISCO_IOS, config_txt)


def test_analyze_structural_diff(source_config, target_config):
    """HierarchicalDiffAnalyzer.analyze_structural_diff が正常に動作すること。"""
    diff_analyzer = HierarchicalDiffAnalyzer()
    diff_analyzer.analyze_structural_diff(source_config, target_config)


class TestTextAlignedDiffComparator:
    """TextAlignedDiffComparator のテストクラス。"""

    def test_equal_texts(self):
        """完全に同じテキストの場合、行数が一致し内容も等しいこと。"""
        source = "line1\nline2\nline3"
        target = "line1\nline2\nline3"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 3
        assert source_aligned == ["line1", "line2", "line3"]
        assert target_aligned == ["line1", "line2", "line3"]

    def test_insert_lines(self):
        """target側にのみ行が存在する場合、source側に空行が挿入されること。"""
        source = "line1\nline3"
        target = "line1\nline2\nline3"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 3
        assert source_aligned == ["line1", "", "line3"]
        assert target_aligned == ["line1", "line2", "line3"]

    def test_delete_lines(self):
        """source側にのみ行が存在する場合、target側に空行が挿入されること。"""
        source = "line1\nline2\nline3"
        target = "line1\nline3"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 3
        assert source_aligned == ["line1", "line2", "line3"]
        assert target_aligned == ["line1", "", "line3"]

    def test_replace_lines(self):
        """行が置換された場合、高さが揃うこと。"""
        source = "line1\nline2\nline4"
        target = "line1\nline3\nline4"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 3
        assert source_aligned == ["line1", "line2", "line4"]
        assert target_aligned == ["line1", "line3", "line4"]

    def test_replace_multiple_lines(self):
        """複数行が置換された場合（行数が異なる）でも高さが揃うこと。"""
        source = "line1\nold_line1\nold_line2\nline4"
        target = "line1\nnew_line\nline4"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 4
        assert source_aligned == ["line1", "old_line1", "old_line2", "line4"]
        assert target_aligned == ["line1", "new_line", "", "line4"]

    def test_complex_diff(self):
        """複雑な差分でも高さが揃い、共通行が先頭・末尾に存在すること。"""
        source = "line1\nline2\nline5\nline6"
        target = "line1\nline3\nline4\nline6"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned)
        assert source_aligned[0] == target_aligned[0] == "line1"
        assert source_aligned[-1] == target_aligned[-1] == "line6"

    def test_empty_texts(self):
        """空のテキストの場合、結果も空リストであること。"""
        source = ""
        target = ""

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 0

    def test_one_empty_text(self):
        """一方が空テキストの場合、もう一方の行数に合わせて空行が入ること。"""
        source = "line1\nline2\nline3"
        target = ""

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 3
        assert source_aligned == ["line1", "line2", "line3"]
        assert target_aligned == ["", "", ""]

    def test_compare_and_align_with_diff_info_equal(self):
        """差分情報付き比較 - 同じテキストはすべて equal になること。"""
        source = "line1\nline2\nline3"
        target = "line1\nline2\nline3"

        source_lines, target_lines, diff_types = (
            TextAlignedDiffComparator.compare_and_align_with_diff_info(
                source, target
            )
        )

        assert len(source_lines) == len(target_lines) == len(diff_types) == 3
        assert all(dt == "equal" for dt in diff_types)

    def test_compare_and_align_with_diff_info_delete(self):
        """差分情報付き比較 - 削除行が delete タイプになること。"""
        source = "line1\nline2\nline3"
        target = "line1\nline3"

        source_lines, target_lines, diff_types = (
            TextAlignedDiffComparator.compare_and_align_with_diff_info(
                source, target
            )
        )

        assert len(source_lines) == len(target_lines) == len(diff_types) == 3
        assert diff_types[0] == "equal"
        assert diff_types[1] == "delete"
        assert diff_types[2] == "equal"
        assert source_lines[1] == "line2"
        assert target_lines[1] == ""

    def test_compare_and_align_with_diff_info_insert(self):
        """差分情報付き比較 - 挿入行が insert タイプになること。"""
        source = "line1\nline3"
        target = "line1\nline2\nline3"

        source_lines, target_lines, diff_types = (
            TextAlignedDiffComparator.compare_and_align_with_diff_info(
                source, target
            )
        )

        assert len(source_lines) == len(target_lines) == len(diff_types) == 3
        assert diff_types[0] == "equal"
        assert diff_types[1] == "insert"
        assert diff_types[2] == "equal"
        assert source_lines[1] == ""
        assert target_lines[1] == "line2"

    def test_compare_and_align_with_diff_info_replace(self):
        """差分情報付き比較 - 置換行が replace タイプになること。"""
        source = "line1\nline2\nline4"
        target = "line1\nline3\nline4"

        source_lines, target_lines, diff_types = (
            TextAlignedDiffComparator.compare_and_align_with_diff_info(
                source, target
            )
        )

        assert len(source_lines) == len(target_lines) == len(diff_types) == 3
        assert diff_types[0] == "equal"
        assert diff_types[1] == "replace"
        assert diff_types[2] == "equal"
        assert source_lines[1] == "line2"
        assert target_lines[1] == "line3"

    def test_hierarchical_diff_same_text_different_parent(self):
        """異なる親ブロック下の同一テキストが誤ってマッチされないこと。

        no shutdown のような共通行が、異なる親インターフェース配下にある場合に
        誤ったマッチングが行われないことを確認する（実際のバグの再現テスト）。
        """
        source = (
            "interface GigabitEthernet0/0\n"
            " no shutdown\n"
            "!\n"
            "interface GigabitEthernet0/1\n"
            " ip address 10.0.0.1 255.255.255.0\n"
            " no shutdown\n"
            "!"
        )
        target = (
            "interface GigabitEthernet0/0\n"
            " no shutdown\n"
            "!\n"
            "interface GigabitEthernet0/1\n"
            " ip address 10.0.0.1 255.255.255.0\n"
            " no shutdown\n"
            "!\n"
            "interface GigabitEthernet0/2\n"
            " ip address 172.16.0.1 255.255.255.0\n"
            " no shutdown\n"
            "!"
        )

        source_lines, target_lines, diff_types = (
            TextAlignedDiffComparator.compare_and_align_with_diff_info(
                source, target
            )
        )

        assert len(source_lines) == len(target_lines) == len(diff_types)

        # GigabitEthernet0/0 のブロックは equal のはず
        assert source_lines[0] == target_lines[0] == "interface GigabitEthernet0/0"
        assert diff_types[0] == "equal"
        assert source_lines[1] == target_lines[1] == " no shutdown"
        assert diff_types[1] == "equal"

        # GigabitEthernet0/1 配下の no shutdown は Gi0/2 の no shutdown と
        # 誤ってマッチされてはならない（Gi0/1 行は equal のはず）
        gi01_no_shutdown_idx = source_lines.index(
            " no shutdown",
            source_lines.index("interface GigabitEthernet0/1"),
        )
        assert diff_types[gi01_no_shutdown_idx] == "equal"

        # GigabitEthernet0/2 ブロックは insert のはず
        gi02_idx = target_lines.index("interface GigabitEthernet0/2")
        assert source_lines[gi02_idx] == ""
        assert diff_types[gi02_idx] == "insert"


class TestStructuralDiffComparator:
    """compare_and_align_with_structural_diff_info のテストクラス。"""

    def test_equal_configs(self):
        """同一コンフィグはすべて equal になること。"""
        config = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            " no shutdown\n"
            "!"
        )
        src_lines, tgt_lines, src_types, tgt_types, src_keys, tgt_keys = (
            TextAlignedDiffComparator
            .compare_and_align_with_structural_diff_info(
                config, config, Platform.CISCO_IOS
            )
        )

        assert len(src_lines) == len(tgt_lines)
        assert all(t == "equal" for t in src_types)
        assert all(t == "equal" for t in tgt_types)

    def test_deleted_interface(self):
        """source にのみ存在するインターフェースブロックが delete になること。"""
        source = (
            "interface GigabitEthernet0/0\n"
            " no shutdown\n"
            "!\n"
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )
        target = (
            "interface GigabitEthernet0/0\n"
            " no shutdown\n"
            "!"
        )
        src_lines, tgt_lines, src_types, tgt_types, src_keys, tgt_keys = (
            TextAlignedDiffComparator
            .compare_and_align_with_structural_diff_info(
                source, target, Platform.CISCO_IOS
            )
        )

        assert len(src_lines) == len(tgt_lines) == len(src_types)

        gi01_idx = src_lines.index("interface GigabitEthernet0/1")
        assert src_types[gi01_idx] == "delete"
        assert tgt_lines[gi01_idx] == ""
        assert tgt_types[gi01_idx] == "empty"

    def test_inserted_interface(self):
        """target にのみ存在するインターフェースブロックが insert になること。"""
        source = (
            "interface GigabitEthernet0/0\n"
            " no shutdown\n"
            "!"
        )
        target = (
            "interface GigabitEthernet0/0\n"
            " no shutdown\n"
            "!\n"
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )
        src_lines, tgt_lines, src_types, tgt_types, src_keys, tgt_keys = (
            TextAlignedDiffComparator
            .compare_and_align_with_structural_diff_info(
                source, target, Platform.CISCO_IOS
            )
        )

        assert len(src_lines) == len(tgt_lines) == len(tgt_types)

        gi01_idx = tgt_lines.index("interface GigabitEthernet0/1")
        assert tgt_types[gi01_idx] == "insert"
        assert src_lines[gi01_idx] == ""
        assert src_types[gi01_idx] == "empty"

    def test_different_order_becomes_reorder(self):
        """記載順が異なる行は reorder になり、delete/insert にならないこと。"""
        source = (
            "interface GigabitEthernet0/0\n"
            " no shutdown\n"
            "!\n"
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )
        target = (
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!\n"
            "interface GigabitEthernet0/0\n"
            " no shutdown\n"
            "!"
        )
        src_lines, tgt_lines, src_types, tgt_types, src_keys, tgt_keys = (
            TextAlignedDiffComparator
            .compare_and_align_with_structural_diff_info(
                source, target, Platform.CISCO_IOS
            )
        )

        assert "delete" not in src_types
        assert "insert" not in tgt_types
        assert "reorder" in src_types
        assert "reorder" in tgt_types

    def test_reorder_detection(self):
        """記載順が異なる行がreorderとしてハイライトされること。

        クリックジャンプに必要な src_keys / tgt_keys の reorder キーが
        両側で一致することも確認する。
        """
        source = (
            "interface GigabitEthernet0/0"
            "\n no shutdown"
            "\n!"
            "\ninterface GigabitEthernet0/1"
            "\n no shutdown"
            "\n!"
        )
        target = (
            "interface GigabitEthernet0/1"
            "\n no shutdown"
            "\n!"
            "\ninterface GigabitEthernet0/0"
            "\n no shutdown"
            "\n!"
        )
        src_lines, tgt_lines, src_types, tgt_types, src_keys, tgt_keys = (
            TextAlignedDiffComparator
            .compare_and_align_with_structural_diff_info(
                source, target, Platform.CISCO_IOS
            )
        )

        assert "delete" not in src_types
        assert "insert" not in tgt_types
        assert "reorder" in src_types
        assert "reorder" in tgt_types

        # reorder のキーが両側で一致すること（クリックジャンプに必要）
        src_reorder_keys = {
            src_keys[i] for i, t in enumerate(src_types) if t == "reorder"
        }
        tgt_reorder_keys = {
            tgt_keys[i] for i, t in enumerate(tgt_types) if t == "reorder"
        }
        assert src_reorder_keys == tgt_reorder_keys
