import pytest
from hier_config import get_hconfig, Platform
from hier_config.utils import read_text_from_file

from src.diff import HierarchicalDiffAnalyzer, TextAlignedDiffComparator

@pytest.fixture
def source_config():
    # テスト用のHConfigオブジェクトを作成
    config_txt = read_text_from_file("tests/fixtures/source.txt")
    config = get_hconfig(Platform.CISCO_IOS, config_txt)
    return config


@pytest.fixture
def target_config():
    # テスト用のHConfigオブジェクトを作成
    config_txt = read_text_from_file("tests/fixtures/target.txt")
    config = get_hconfig(Platform.CISCO_IOS, config_txt)
    return config


def test_analyze_structural_diff(source_config, target_config):
    diff_analyzer = HierarchicalDiffAnalyzer()
    diff_analyzer.analyze_structural_diff(source_config, target_config)


class TestTextAlignedDiffComparator:
    """TextAlignedDiffComparatorのテストクラス"""

    def test_equal_texts(self):
        """完全に同じテキストの場合"""
        source = "line1\nline2\nline3"
        target = "line1\nline2\nline3"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 3
        assert source_aligned == ["line1", "line2", "line3"]
        assert target_aligned == ["line1", "line2", "line3"]

    def test_insert_lines(self):
        """target側にのみ行が存在する場合"""
        source = "line1\nline3"
        target = "line1\nline2\nline3"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 3
        assert source_aligned == ["line1", "", "line3"]
        assert target_aligned == ["line1", "line2", "line3"]

    def test_delete_lines(self):
        """source側にのみ行が存在する場合"""
        source = "line1\nline2\nline3"
        target = "line1\nline3"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 3
        assert source_aligned == ["line1", "line2", "line3"]
        assert target_aligned == ["line1", "", "line3"]

    def test_replace_lines(self):
        """行が置換された場合"""
        source = "line1\nline2\nline4"
        target = "line1\nline3\nline4"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 3
        assert source_aligned == ["line1", "line2", "line4"]
        assert target_aligned == ["line1", "line3", "line4"]

    def test_replace_multiple_lines(self):
        """複数行が置換された場合（行数が異なる）"""
        source = "line1\nold_line1\nold_line2\nline4"
        target = "line1\nnew_line\nline4"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 4
        assert source_aligned == ["line1", "old_line1", "old_line2", "line4"]
        assert target_aligned == ["line1", "new_line", "", "line4"]

    def test_complex_diff(self):
        """複雑な差分の場合"""
        source = "line1\nline2\nline5\nline6"
        target = "line1\nline3\nline4\nline6"

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        # 高さが揃っていることを確認
        assert len(source_aligned) == len(target_aligned)

        # 最初と最後の行が一致していることを確認
        assert source_aligned[0] == target_aligned[0] == "line1"
        assert source_aligned[-1] == target_aligned[-1] == "line6"

    def test_empty_texts(self):
        """空のテキストの場合"""
        source = ""
        target = ""

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 0

    def test_one_empty_text(self):
        """一方が空のテキストの場合"""
        source = "line1\nline2\nline3"
        target = ""

        source_aligned, target_aligned = (
            TextAlignedDiffComparator.compare_and_align(source, target)
        )

        assert len(source_aligned) == len(target_aligned) == 3
        assert source_aligned == ["line1", "line2", "line3"]
        assert target_aligned == ["", "", ""]

    def test_compare_and_align_with_diff_info_equal(self):
        """差分情報付き比較 - 同じテキスト"""
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
        """差分情報付き比較 - 削除"""
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
        """差分情報付き比較 - 挿入"""
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
        """差分情報付き比較 - 置換"""
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
        """階層構造を持つテキストの比較

        異なる親ブロック下にある同じテキスト（no shutdown等）が
        誤ってマッチされないことを確認する（実際のバグの再現テスト）
        """
        # sourceはGi0/1配下にno shutdown
        source = (
            "interface GigabitEthernet0/0\n"
            " no shutdown\n"
            "!\n"
            "interface GigabitEthernet0/1\n"
            " ip address 10.0.0.1 255.255.255.0\n"
            " no shutdown\n"
            "!"
        )
        # targetはGi0/1とGi0/2（新規追加）配下にno shutdown
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

        # GigabitEthernet0/0のブロックはequalのはず
        assert source_lines[0] == target_lines[0] == "interface GigabitEthernet0/0"
        assert diff_types[0] == "equal"
        assert source_lines[1] == target_lines[1] == " no shutdown"
        assert diff_types[1] == "equal"

        # GigabitEthernet0/1配下のno shutdownはGi0/2のno shutdownと
        # 誤ってマッチされてはならない（Gi0/1行はequalのはず）
        gi01_no_shutdown_idx = source_lines.index(
            " no shutdown",
            source_lines.index("interface GigabitEthernet0/1")
        )
        assert diff_types[gi01_no_shutdown_idx] == "equal"

        # GigabitEthernet0/2ブロックはinsertのはず
        gi02_idx = target_lines.index("interface GigabitEthernet0/2")
        assert source_lines[gi02_idx] == ""
        assert diff_types[gi02_idx] == "insert"


class TestStructuralDiffComparator:
    """compare_and_align_with_structural_diff_infoのテストクラス"""

    def test_equal_configs(self):
        """同一コンフィグはすべてequalになること"""
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
        """sourceにのみ存在するinterfaceブロックがdeleteになること"""
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

        # Gi0/1配下の行はsource側でdeleteになるはず
        gi01_idx = src_lines.index("interface GigabitEthernet0/1")
        assert src_types[gi01_idx] == "delete"
        # target側は空行（empty）になるはず
        assert tgt_lines[gi01_idx] == ""
        assert tgt_types[gi01_idx] == "empty"

    def test_inserted_interface(self):
        """targetにのみ存在するinterfaceブロックがinsertになること"""
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

        # Gi0/1配下の行はtarget側でinsertになるはず
        gi01_idx = tgt_lines.index("interface GigabitEthernet0/1")
        assert tgt_types[gi01_idx] == "insert"
        # source側は空行（empty）になるはず
        assert src_lines[gi01_idx] == ""
        assert src_types[gi01_idx] == "empty"

    def test_different_order_becomes_reorder(self):
        """記載順が異なる行はreorderタイプになり、deleteやinsertにはならないこと"""
        source = (
            "interface GigabitEthernet0/0\n"
            " no shutdown\n"
            "!\n"
            "interface GigabitEthernet0/1\n"
            " no shutdown\n"
            "!"
        )
        # sourceとtargetでinterfaceの順番を入れ替え
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

        # 両方に同じ内容が存在するため、deleteもinsertもないはず
        assert "delete" not in src_types
        assert "insert" not in tgt_types
        # 順番が異なるためreorderになるはず
        assert "reorder" in src_types
        assert "reorder" in tgt_types

    def test_reorder_detection(self):
        """記載順が異なる行がreorderとしてハイライトされること"""
        source = (
            "interface GigabitEthernet0/0"
            "\n no shutdown"
            "\n!"
            "\ninterface GigabitEthernet0/1"
            "\n no shutdown"
            "\n!"
        )
        # sourceとtargetでinterfaceの順番を入れ替え
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

        # deleteもinsertもなく、reorderが存在するはず
        assert "delete" not in src_types
        assert "insert" not in tgt_types
        assert "reorder" in src_types
        assert "reorder" in tgt_types

        # reorderのsrc_keyとtgt_keyが一致すること（クリックジャンプに必要）
        src_reorder_keys = {
            src_keys[i] for i, t in enumerate(src_types) if t == "reorder"
        }
        tgt_reorder_keys = {
            tgt_keys[i] for i, t in enumerate(tgt_types) if t == "reorder"
        }
        # 両側のreorderキーが一致するはず
        assert src_reorder_keys == tgt_reorder_keys
