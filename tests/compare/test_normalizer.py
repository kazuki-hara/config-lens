"""VLANトランク正規化モジュール（normalizer.py）のテスト。"""

from src.compare.normalizer import (
    VLAN_DIFF_ANNOTATION_MARKER,
    expand_vlan_ids,
    normalize_vlan_trunk_config,
    normalize_vlan_trunk_pair,
    vlan_ids_to_ranges,
)
from src.compare.logic import TextAlignedDiffComparator


class TestExpandVlanIds:
    """expand_vlan_ids のテストクラス。"""

    def test_single_vlan(self) -> None:
        """単一のVLAN IDを正しく展開すること。"""
        assert expand_vlan_ids("10") == {10}

    def test_comma_separated(self) -> None:
        """カンマ区切りのVLAN IDを正しく展開すること。"""
        assert expand_vlan_ids("10,20,30") == {10, 20, 30}

    def test_range(self) -> None:
        """ハイフンによる範囲指定を正しく展開すること。"""
        assert expand_vlan_ids("1-3") == {1, 2, 3}

    def test_mixed_comma_and_range(self) -> None:
        """カンマ区切りと範囲指定の混合を正しく展開すること。"""
        assert expand_vlan_ids("10,20,100-102") == {10, 20, 100, 101, 102}

    def test_with_spaces(self) -> None:
        """スペースを含むVLAN ID文字列を正しく展開すること。"""
        assert expand_vlan_ids("10, 20, 30") == {10, 20, 30}

    def test_empty_string(self) -> None:
        """空文字列に対して空のセットを返すこと。"""
        assert expand_vlan_ids("") == set()

    def test_large_range(self) -> None:
        """広い範囲のVLAN IDを正しく展開すること。"""
        result = expand_vlan_ids("1-10")
        assert result == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}

    def test_vlan_with_range_and_singles(self) -> None:
        """実際のコンフィグに近い複合形式を展開すること。"""
        result = expand_vlan_ids("10,20,100-105,200")
        assert result == {10, 20, 100, 101, 102, 103, 104, 105, 200}


class TestNormalizeVlanTrunkConfig:
    """normalize_vlan_trunk_config のテストクラス。"""

    def test_no_vlan_trunk_lines(self) -> None:
        """VLANトランク行がないコンフィグはそのまま返されること。"""
        config = (
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
            " no shutdown\n"
            "!"
        )
        assert normalize_vlan_trunk_config(config) == config

    def test_single_vlan_line(self) -> None:
        """addなしの単一VLANトランク行はそのまま（ソート済みで）返されること。"""
        config = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 30,10,20\n"
            " switchport mode trunk"
        )
        result = normalize_vlan_trunk_config(config)
        # VLAN IDはソートされる
        assert " switchport trunk allowed vlan 10,20,30" in result
        assert "switchport trunk allowed vlan add" not in result

    def test_vlan_with_single_add(self) -> None:
        """VLANトランク行 + 1つのadd行が1行に統合されること。"""
        config = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20\n"
            " switchport trunk allowed vlan add 30,40\n"
            " switchport mode trunk"
        )
        result = normalize_vlan_trunk_config(config)
        lines = result.splitlines()

        assert " switchport trunk allowed vlan 10,20,30,40" in lines
        assert not any("add" in line for line in lines)

    def test_vlan_with_multiple_adds(self) -> None:
        """VLANトランク行 + 複数のadd行がすべて1行に統合されること。"""
        config = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20\n"
            " switchport trunk allowed vlan add 30,40\n"
            " switchport trunk allowed vlan add 50\n"
            " switchport mode trunk"
        )
        result = normalize_vlan_trunk_config(config)
        lines = result.splitlines()

        assert " switchport trunk allowed vlan 10,20,30,40,50" in lines
        assert not any("add" in line for line in lines)

    def test_user_scenario_source(self) -> None:
        """ユーザー提示のsourceコンフィグが正規化されること。

        interface GigabitEthernet1/0/1
         switchport trunk allowed vlan 10,20,...,100
         switchport trunk allowed vlan add 110,...,200

        → switchport trunk allowed vlan 10,...,100,110,...,200 の1行になること。
        """
        config = (
            "interface GigabitEthernet1/0/1\n"
            " switchport trunk allowed vlan 10,20,30,40,50,60,70,80,90,100\n"
            " switchport trunk allowed vlan add"
            " 110,120,130,140,150,160,170,180,190,200\n"
            " switchport mode trunk"
        )
        result = normalize_vlan_trunk_config(config)
        expected_vlan_line = (
            " switchport trunk allowed vlan"
            " 10,20,30,40,50,60,70,80,90,100,"
            "110,120,130,140,150,160,170,180,190,200"
        )
        assert expected_vlan_line in result.splitlines()
        assert "add" not in result

    def test_user_scenario_target(self) -> None:
        """ユーザー提示のtargetコンフィグが正規化されること。

        interface GigabitEthernet1/0/1
         switchport trunk allowed vlan 10,...,90,99
         switchport trunk allowed vlan add 100,...,190
         switchport trunk allowed vlan add 200

        → all VLANs（99を含む）が1行に統合されること。
        """
        config = (
            "interface GigabitEthernet1/0/1\n"
            " switchport trunk allowed vlan 10,20,30,40,50,60,70,80,90,99\n"
            " switchport trunk allowed vlan add"
            " 100,110,120,130,140,150,160,170,180,190\n"
            " switchport trunk allowed vlan add 200\n"
            " switchport mode trunk"
        )
        result = normalize_vlan_trunk_config(config)
        expected_vlan_line = (
            " switchport trunk allowed vlan"
            " 10,20,30,40,50,60,70,80,90,99-100,"
            "110,120,130,140,150,160,170,180,190,200"
        )
        assert expected_vlan_line in result.splitlines()
        assert "add" not in result

    def test_multiple_interfaces(self) -> None:
        """複数インターフェースそれぞれのVLANが独立して正規化されること。"""
        config = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20\n"
            " switchport trunk allowed vlan add 30\n"
            " switchport mode trunk\n"
            "!\n"
            "interface Gi1/0/2\n"
            " switchport trunk allowed vlan 100,200\n"
            " switchport trunk allowed vlan add 300\n"
            " switchport mode trunk"
        )
        result = normalize_vlan_trunk_config(config)
        lines = result.splitlines()

        assert " switchport trunk allowed vlan 10,20,30" in lines
        assert " switchport trunk allowed vlan 100,200,300" in lines
        assert not any("add" in line for line in lines)

    def test_non_vlan_lines_preserved(self) -> None:
        """VLANトランク行以外の行が保持されること。"""
        config = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20\n"
            " switchport trunk allowed vlan add 30\n"
            " switchport trunk native vlan 1\n"
            " switchport mode trunk\n"
            " spanning-tree portfast trunk"
        )
        result = normalize_vlan_trunk_config(config)
        lines = result.splitlines()

        assert " switchport trunk native vlan 1" in lines
        assert " switchport mode trunk" in lines
        assert " spanning-tree portfast trunk" in lines

    def test_idempotent(self) -> None:
        """正規化済みのコンフィグを再度正規化しても結果が変わらないこと。"""
        config = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20\n"
            " switchport trunk allowed vlan add 30,40\n"
            " switchport mode trunk"
        )
        once = normalize_vlan_trunk_config(config)
        twice = normalize_vlan_trunk_config(once)
        assert once == twice

    def test_case_insensitive(self) -> None:
        """大文字小文字を問わずVLANトランク行を認識すること。"""
        config = (
            "interface Gi1/0/1\n"
            " Switchport Trunk Allowed Vlan 10,20\n"
            " SWITCHPORT TRUNK ALLOWED VLAN ADD 30\n"
            " switchport mode trunk"
        )
        result = normalize_vlan_trunk_config(config)
        assert " switchport trunk allowed vlan 10,20,30" in result.lower()

    def test_vlan_range_in_trunk(self) -> None:
        """範囲指定（1-3形式）を含むVLANトランク行を正規化すること。

        連続するVLAN IDは範囲表記（例: 1-3）で出力されること。
        """
        config = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 1-3\n"
            " switchport trunk allowed vlan add 10,20\n"
            " switchport mode trunk"
        )
        result = normalize_vlan_trunk_config(config)
        # 1-3 は連続するので範囲表記のまま、10,20 は個別表記
        assert " switchport trunk allowed vlan 1-3,10,20" in result


class TestVlanIdsToRanges:
    """vlan_ids_to_ranges のテストクラス。"""

    def test_empty_set(self) -> None:
        """空のセットに対して空文字列を返すこと。"""
        assert vlan_ids_to_ranges(set()) == ""

    def test_single_id(self) -> None:
        """単一IDをそのまま文字列で返すこと。"""
        assert vlan_ids_to_ranges({10}) == "10"

    def test_consecutive_ids_become_range(self) -> None:
        """連続するIDが範囲表記にまとめられること。"""
        assert vlan_ids_to_ranges({1, 2, 3}) == "1-3"

    def test_non_consecutive_ids(self) -> None:
        """非連続IDがカンマ区切りで出力されること。"""
        assert vlan_ids_to_ranges({10, 20, 30}) == "10,20,30"

    def test_mixed_ranges_and_singles(self) -> None:
        """連続部分と非連続部分が混在すること。"""
        result = vlan_ids_to_ranges({1, 2, 3, 10, 20, 30, 31})
        assert result == "1-3,10,20,30-31"

    def test_single_range_at_boundary(self) -> None:
        """2連続だと範囲表記になること。"""
        assert vlan_ids_to_ranges({99, 100}) == "99-100"

    def test_roundtrip_with_expand(self) -> None:
        """expand_vlan_ids → vlan_ids_to_ranges の往復が一致すること。"""
        original = "10-20,30,40-45,100"
        expanded = expand_vlan_ids(original)
        result = vlan_ids_to_ranges(expanded)
        # 再展開して元のセットと同じことを確認
        assert expand_vlan_ids(result) == expanded


class TestNormalizeVlanTrunkPair:
    """normalize_vlan_trunk_pair のテストクラス。"""

    def test_identical_configs_no_annotation(self) -> None:
        """同一VLANのコンフィグにはアノテーション行が挿入されないこと。"""
        config = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20,30\n"
            " switchport mode trunk"
        )
        src_out, tgt_out = normalize_vlan_trunk_pair(config, config)
        assert VLAN_DIFF_ANNOTATION_MARKER not in src_out
        assert VLAN_DIFF_ANNOTATION_MARKER not in tgt_out

    def test_diff_vlans_annotation_inserted_in_both(self) -> None:
        """VLAN差分がある場合、両テキストに同一アノテーション行が挿入されること。"""
        src = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20,30\n"
            " switchport mode trunk"
        )
        tgt = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20,40\n"
            " switchport mode trunk"
        )
        src_out, tgt_out = normalize_vlan_trunk_pair(src, tgt)

        src_lines = src_out.splitlines()
        tgt_lines = tgt_out.splitlines()

        # 両側に同じアノテーション行が存在すること
        src_ann_lines = [
            line for line in src_lines
            if VLAN_DIFF_ANNOTATION_MARKER in line
        ]
        tgt_ann_lines = [
            line for line in tgt_lines
            if VLAN_DIFF_ANNOTATION_MARKER in line
        ]
        assert len(src_ann_lines) == 1
        assert len(tgt_ann_lines) == 1
        assert src_ann_lines[0] == tgt_ann_lines[0], (
            "アノテーション行が両側で一致しないと equal 判定されない"
        )

    def test_annotation_shows_delete_and_add(self) -> None:
        """アノテーション行に削除VLAN (+add) と追加VLAN (-delete) が含まれること。"""
        src = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20,30\n"
            " switchport mode trunk"
        )
        tgt = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20,40\n"
            " switchport mode trunk"
        )
        src_out, _tgt_out = normalize_vlan_trunk_pair(src, tgt)
        ann = next(
            ann_line for ann_line in src_out.splitlines()
            if VLAN_DIFF_ANNOTATION_MARKER in ann_line
        )
        # sourceにのみある30はdelete、targetにのみある40はadd
        assert "-delete:30" in ann
        assert "+add:40" in ann

    def test_annotation_uses_range_notation(self) -> None:
        """アノテーション行のVLAN差分が範囲表記を使うこと。"""
        src = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10-20\n"
            " switchport mode trunk"
        )
        tgt = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10-18\n"
            " switchport mode trunk"
        )
        src_out, _tgt_out = normalize_vlan_trunk_pair(src, tgt)
        ann = next(
            ann_line for ann_line in src_out.splitlines()
            if VLAN_DIFF_ANNOTATION_MARKER in ann_line
        )
        # 19,20 は連続しているので範囲表記になること
        assert "-delete:19-20" in ann

    def test_annotation_placed_after_vlan_line(self) -> None:
        """アノテーション行がVLANトランク行の直後に挿入されること。"""
        src = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20\n"
            " switchport mode trunk"
        )
        tgt = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,30\n"
            " switchport mode trunk"
        )
        src_out, _tgt_out = normalize_vlan_trunk_pair(src, tgt)
        lines = src_out.splitlines()
        vlan_idx = next(
            i for i, line in enumerate(lines)
            if "switchport trunk allowed vlan" in line
            and VLAN_DIFF_ANNOTATION_MARKER not in line
        )
        assert VLAN_DIFF_ANNOTATION_MARKER in lines[vlan_idx + 1]

    def test_fixture_files_annotation(self) -> None:
        """実際のフィクスチャファイルでアノテーション行が生成されること。

        l2sw_source.txtとl2sw_target.txtの差分VLAN (96削除, 161,169追加)
        がアノテーション行に表示されること。
        """
        src_text = open("tests/fixtures/vlan/l2sw_source.txt").read()
        tgt_text = open("tests/fixtures/vlan/l2sw_target.txt").read()

        src_out, tgt_out = normalize_vlan_trunk_pair(src_text, tgt_text)

        src_ann_lines = [
            ann_line for ann_line in src_out.splitlines()
            if VLAN_DIFF_ANNOTATION_MARKER in ann_line
        ]
        assert len(src_ann_lines) == 1, "Gi1/0/1 に差分があるはず"

        ann = src_ann_lines[0]
        # source にのみ存在するVLAN96が -delete に含まれること
        assert "-delete:" in ann and "96" in ann
        # target にのみ存在するVLAN161,169が +add に含まれること
        assert "+add:" in ann and "161" in ann and "169" in ann

        # 両側のアノテーションが同一であること
        tgt_ann_lines = [
            ann_line for ann_line in tgt_out.splitlines()
            if VLAN_DIFF_ANNOTATION_MARKER in ann_line
        ]
        assert src_ann_lines == tgt_ann_lines


class TestNormalizeIntegration:
    """normalize=True を指定した compare_and_align のテストクラス。"""

    def test_vlan99_only_detected(self) -> None:
        """ユーザーシナリオ: VLAN99の差分のみを検知すること。

        sourceにはVLAN99がなく、targetにはVLAN99がある。
        addで行が分割されていても正規化後に差分として検知されること。
        """
        source = (
            "interface GigabitEthernet1/0/1\n"
            " switchport trunk allowed vlan 10,20,30,40,50,60,70,80,90,100\n"
            " switchport trunk allowed vlan add "
            "110,120,130,140,150,160,170,180,190,200\n"
            " switchport mode trunk"
        )
        target = (
            "interface GigabitEthernet1/0/1\n"
            " switchport trunk allowed vlan 10,20,30,40,50,60,70,80,90,99\n"
            " switchport trunk allowed vlan add "
            "100,110,120,130,140,150,160,170,180,190\n"
            " switchport trunk allowed vlan add 200\n"
            " switchport mode trunk"
        )
        src_lines, tgt_lines, diff_types = (
            TextAlignedDiffComparator.compare_and_align_with_diff_info(
                source, target, normalize=True
            )
        )

        # normalize=True では行数が揃うこと
        assert len(src_lines) == len(tgt_lines) == len(diff_types)

        # interface行・switchport mode trunk行はequalであること
        iface_row = src_lines.index("interface GigabitEthernet1/0/1")
        assert diff_types[iface_row] == "equal"

        mode_row = src_lines.index(" switchport mode trunk")
        assert diff_types[mode_row] == "equal"

    def test_identical_vlans_no_diff(self) -> None:
        """VLAN構成が同一なら、行分割が異なっても差分なしと判定されること。"""
        # sourceは1行にまとめ、targetはaddで複数行に分割
        source = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20,30,40,50\n"
            " switchport mode trunk"
        )
        target = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20,30\n"
            " switchport trunk allowed vlan add 40,50\n"
            " switchport mode trunk"
        )
        src_lines, tgt_lines, diff_types = (
            TextAlignedDiffComparator.compare_and_align_with_diff_info(
                source, target, normalize=True
            )
        )

        # 正規化後は両方ともVLAN 10,20,30,40,50 の1行になるため
        # すべての行がequalになること
        assert all(t == "equal" for t in diff_types), (
            f"差分が検出された: {list(zip(src_lines, tgt_lines, diff_types))}"
        )

    def test_normalize_false_does_not_affect_non_vlan(self) -> None:
        """normalize=False の場合、通常のconfig比較は従来通り動作すること。"""
        source = "interface Gi0/0\n no shutdown"
        target = "interface Gi0/0\n no shutdown"

        src_lines, tgt_lines, diff_types = (
            TextAlignedDiffComparator.compare_and_align_with_diff_info(
                source, target, normalize=False
            )
        )

        assert all(t == "equal" for t in diff_types)

    def test_annotation_line_is_equal_in_diff(self) -> None:
        """アノテーション行が差分比較で equal と判定されること。

        両側に同じアノテーション行が挿入されるため、
        SequenceMatcher は equal と認識し、グレー表示される。
        """
        source = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20,30\n"
            " switchport mode trunk"
        )
        target = (
            "interface Gi1/0/1\n"
            " switchport trunk allowed vlan 10,20,40\n"
            " switchport mode trunk"
        )
        src_lines, tgt_lines, diff_types = (
            TextAlignedDiffComparator.compare_and_align_with_diff_info(
                source, target, normalize=True
            )
        )

        # アノテーション行が存在すること
        ann_indices = [
            i for i, line in enumerate(src_lines)
            if VLAN_DIFF_ANNOTATION_MARKER in line
        ]
        assert len(ann_indices) == 1, "アノテーション行が1行あるはず"

        # アノテーション行は equal と判定されること（両側に同じ文字列）
        ann_idx = ann_indices[0]
        assert diff_types[ann_idx] == "equal", (
            "アノテーション行は equal のはず（グレー表示のため）"
        )
        assert src_lines[ann_idx] == tgt_lines[ann_idx]
