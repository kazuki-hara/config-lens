"""比較ロジックモジュール。

テキストおよびネットワーク機器コンフィグの差分計算ロジックを提供する。
"""

import difflib

from hier_config import HConfig, Platform, get_hconfig

from src.compare.normalizer import normalize_vlan_trunk_pair
from src.utils import (
    calculate_hierarchical_path,
    remove_plus_minus_from_diff_line,
)


class HierarchicalDiffAnalyzer:
    """階層構造を持つコンフィグの差分を解析するクラス。"""

    @staticmethod
    def analyze_structural_diff(
        source_config: HConfig,
        target_config: HConfig,
    ) -> dict[str, list[list[str]]]:
        """コンフィグ構造の差分を出力する。

        Args:
            source_config: 比較元の running-config
            target_config: 比較先の running-config

        Returns:
            差分情報の辞書。キーは以下の通り。

            - ``additional_parts``: target にのみ存在する行のパスリスト
            - ``deletional_parts``: source にのみ存在する行のパスリスト
            - ``non_changed_parts``: 両方に存在する行のパスリスト
        """
        structural_diff = list(source_config.unified_diff(target_config))
        cleaned_diff = [
            remove_plus_minus_from_diff_line(line) for line in structural_diff
        ]
        structural_diff_path_list = calculate_hierarchical_path(cleaned_diff)
        additional_parts: list[list[str]] = []
        deletional_parts: list[list[str]] = []
        non_changed_parts: list[list[str]] = []
        for diff_path, line in zip(structural_diff_path_list, structural_diff):
            if line.lstrip().startswith("+"):
                additional_parts.append(diff_path)
            elif line.lstrip().startswith("-"):
                deletional_parts.append(diff_path)
            else:
                non_changed_parts.append(diff_path)
        return {
            "additional_parts": additional_parts,
            "deletional_parts": deletional_parts,
            "non_changed_parts": non_changed_parts,
        }


class TextAlignedDiffComparator:
    """2つのテキストを比較し、WinMergeのように高さを揃えるクラス。"""

    @staticmethod
    def _build_hierarchical_keys(lines: list[str]) -> list[str]:
        """各行の階層パスをキーとして返す。

        階層パスを使用することで、同じテキストでも異なる階層にある行を
        区別して比較できます。

        Args:
            lines: テキストの行のリスト

        Returns:
            各行の階層パスを連結したキーのリスト

        Example:
            >>> lines = ["interface Gi0/0", " no shutdown"]
            >>> keys = TextAlignedDiffComparator._build_hierarchical_keys(lines)
            >>> keys[1]
            'interface Gi0/0 > no shutdown'
        """
        paths = calculate_hierarchical_path(lines)
        return [" > ".join(path) for path in paths]

    @staticmethod
    def _build_aligned_diff(
        source_lines: list[str],
        target_lines: list[str],
        source_keys: list[str],
        target_keys: list[str],
    ) -> tuple[list[str], list[str], list[str]]:
        """階層パスキーを使って差分を計算し、行を揃える内部メソッド。

        Args:
            source_lines: source側の表示用行リスト
            target_lines: target側の表示用行リスト
            source_keys: source側の比較用キーリスト
            target_keys: target側の比較用キーリスト

        Returns:
            タプル ``(source行リスト, target行リスト, 差分タイプリスト)``。
            差分タイプは ``"equal"``, ``"delete"``, ``"insert"``,
            ``"replace"`` のいずれか。
        """
        aligned_source, aligned_target, src_keys, tgt_keys = (
            TextAlignedDiffComparator._build_aligned_diff_with_keys(
                source_lines, target_lines, source_keys, target_keys
            )
        )
        diff_types: list[str] = []
        for s_key, t_key in zip(src_keys, tgt_keys):
            if s_key == "" and t_key != "":
                diff_types.append("insert")
            elif s_key != "" and t_key == "":
                diff_types.append("delete")
            elif s_key != t_key:
                diff_types.append("replace")
            else:
                diff_types.append("equal")
        return aligned_source, aligned_target, diff_types

    @staticmethod
    def _build_aligned_diff_with_keys(
        source_lines: list[str],
        target_lines: list[str],
        source_keys: list[str],
        target_keys: list[str],
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """階層パスキーを使って差分を計算し、行とキーを揃えて返す内部メソッド。

        Args:
            source_lines: source側の表示用行リスト
            target_lines: target側の表示用行リスト
            source_keys: source側の比較用キーリスト
            target_keys: target側の比較用キーリスト

        Returns:
            タプル ``(source行リスト, target行リスト,
            source整列後キーリスト, target整列後キーリスト)``。
            空行のキーは ``""``。
        """
        aligned_source: list[str] = []
        aligned_target: list[str] = []
        aligned_source_keys: list[str] = []
        aligned_target_keys: list[str] = []

        matcher = difflib.SequenceMatcher(None, source_keys, target_keys)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for i in range(i1, i2):
                    aligned_source.append(source_lines[i])
                    aligned_target.append(target_lines[j1 + (i - i1)])
                    aligned_source_keys.append(source_keys[i])
                    aligned_target_keys.append(target_keys[j1 + (i - i1)])

            elif tag == "replace":
                src_block = source_lines[i1:i2]
                tgt_block = target_lines[j1:j2]
                src_key_block = source_keys[i1:i2]
                tgt_key_block = target_keys[j1:j2]

                # replaceブロック内でも階層キーを再マッチングし、
                # キーが一致する行のみ横に並べる。
                # 一致しない行（異なる設定）は別行としてずらして表示する。
                inner_matcher = difflib.SequenceMatcher(
                    None, src_key_block, tgt_key_block, autojunk=False
                )
                for (
                    inner_tag,
                    ii1,
                    ii2,
                    jj1,
                    jj2,
                ) in inner_matcher.get_opcodes():
                    if inner_tag == "equal":
                        for k in range(ii2 - ii1):
                            aligned_source.append(src_block[ii1 + k])
                            aligned_source_keys.append(src_key_block[ii1 + k])
                            aligned_target.append(tgt_block[jj1 + k])
                            aligned_target_keys.append(tgt_key_block[jj1 + k])
                    else:
                        # replace / delete / insert はすべて別行に配置し、
                        # 明確に異なる設定を横に並べないようにする。
                        for k in range(ii2 - ii1):
                            aligned_source.append(src_block[ii1 + k])
                            aligned_source_keys.append(src_key_block[ii1 + k])
                            aligned_target.append("")
                            aligned_target_keys.append("")
                        for k in range(jj2 - jj1):
                            aligned_source.append("")
                            aligned_source_keys.append("")
                            aligned_target.append(tgt_block[jj1 + k])
                            aligned_target_keys.append(tgt_key_block[jj1 + k])

            elif tag == "delete":
                for i in range(i1, i2):
                    aligned_source.append(source_lines[i])
                    aligned_source_keys.append(source_keys[i])
                    aligned_target.append("")
                    aligned_target_keys.append("")

            elif tag == "insert":
                for j in range(j1, j2):
                    aligned_source.append("")
                    aligned_source_keys.append("")
                    aligned_target.append(target_lines[j])
                    aligned_target_keys.append(target_keys[j])

        return (
            aligned_source,
            aligned_target,
            aligned_source_keys,
            aligned_target_keys,
        )

    @staticmethod
    def compare_and_align(
        source_text: str,
        target_text: str,
        normalize: bool = False,
    ) -> tuple[list[str], list[str]]:
        """2つのテキストを比較し、高さを揃えた行のリストを返す。

        階層パスをキーとして差分を計算するため、同じテキストでも
        異なる親ブロック下にある行は別物として扱われます。

        Args:
            source_text: 比較元のテキスト
            target_text: 比較先のテキスト
            normalize: ``True`` の場合、比較前に L2SW の
                ``switchport trunk allowed vlan`` 行を正規化する。

        Returns:
            高さを揃えた ``(source側行リスト, target側行リスト)``。

        Example:
            >>> source = "line1\\nline2\\nline4"
            >>> target = "line1\\nline3\\nline4"
            >>> source_aligned, target_aligned = (
            ...     TextAlignedDiffComparator.compare_and_align(
            ...         source, target
            ...     )
            ... )
            >>> len(source_aligned) == len(target_aligned)
            True
        """
        if normalize:
            source_text, target_text = normalize_vlan_trunk_pair(
                source_text, target_text
            )
        source_lines = source_text.splitlines()
        target_lines = target_text.splitlines()
        source_keys = TextAlignedDiffComparator._build_hierarchical_keys(
            source_lines
        )
        target_keys = TextAlignedDiffComparator._build_hierarchical_keys(
            target_lines
        )
        aligned_source, aligned_target, _ = (
            TextAlignedDiffComparator._build_aligned_diff(
                source_lines, target_lines, source_keys, target_keys
            )
        )
        return aligned_source, aligned_target

    @staticmethod
    def compare_and_align_with_diff_info(
        source_text: str,
        target_text: str,
        normalize: bool = False,
    ) -> tuple[list[str], list[str], list[str]]:
        """2つのテキストを比較し、高さを揃えた行と差分情報を返す。

        Args:
            source_text: 比較元のテキスト
            target_text: 比較先のテキスト
            normalize: ``True`` の場合、比較前に L2SW の
                ``switchport trunk allowed vlan`` 行を正規化する。

        Returns:
            タプル ``(source行リスト, target行リスト, 差分タイプリスト)``。
            差分タイプは ``"equal"``, ``"delete"``, ``"insert"``,
            ``"replace"`` のいずれか。
        """
        if normalize:
            source_text, target_text = normalize_vlan_trunk_pair(
                source_text, target_text
            )
        source_lines = source_text.splitlines()
        target_lines = target_text.splitlines()
        source_keys = TextAlignedDiffComparator._build_hierarchical_keys(
            source_lines
        )
        target_keys = TextAlignedDiffComparator._build_hierarchical_keys(
            target_lines
        )
        return TextAlignedDiffComparator._build_aligned_diff(
            source_lines, target_lines, source_keys, target_keys
        )

    @staticmethod
    def compare_and_align_with_structural_diff_info(
        source_text: str,
        target_text: str,
        platform: Platform,
        normalize: bool = False,
    ) -> tuple[
        list[str],
        list[str],
        list[str],
        list[str],
        list[str],
        list[str],
    ]:
        """構造的差分に基づき、高さを揃えた行とハイライト情報を返す。

        行の整列はテキスト差分（SequenceMatcher）で行い、ハイライトの判定は
        hier_config の analyze_structural_diff に基づく構造的差分で行います。
        これにより、記載順が異なっても構造的に同一の行はハイライトされません。

        ハイライトタイプ:
            - ``"equal"``  : 両方に存在し、順番も一致
            - ``"delete"`` : sourceにのみ存在
            - ``"insert"`` : targetにのみ存在
            - ``"reorder"``: 両方に存在するが、順番が異なる
            - ``"empty"``  : 対応行がない側のパディング

        Args:
            source_text: 比較元のテキスト
            target_text: 比較先のテキスト
            platform: コンフィグのプラットフォーム
            normalize: ``True`` の場合、比較前に L2SW の
                ``switchport trunk allowed vlan`` 行を正規化する。

        Returns:
            タプル ``(source行リスト, target行リスト,
            source差分タイプリスト, target差分タイプリスト,
            source整列後キーリスト, target整列後キーリスト)``。
        """
        if normalize:
            source_text, target_text = normalize_vlan_trunk_pair(
                source_text, target_text
            )
        source_lines = source_text.splitlines()
        target_lines = target_text.splitlines()
        source_keys = TextAlignedDiffComparator._build_hierarchical_keys(
            source_lines
        )
        target_keys = TextAlignedDiffComparator._build_hierarchical_keys(
            target_lines
        )

        aligned_source, aligned_target, aligned_src_keys, aligned_tgt_keys = (
            TextAlignedDiffComparator._build_aligned_diff_with_keys(
                source_lines, target_lines, source_keys, target_keys
            )
        )

        # 構造的差分の計算
        source_hconfig = get_hconfig(platform, source_text)
        target_hconfig = get_hconfig(platform, target_text)
        structural_diff = HierarchicalDiffAnalyzer.analyze_structural_diff(
            source_hconfig, target_hconfig
        )

        # パスリストをキー文字列のセットに変換（O(1)参照用）
        deletional_key_set: set[str] = {
            " > ".join(p) for p in structural_diff["deletional_parts"]
        }
        additional_key_set: set[str] = {
            " > ".join(p) for p in structural_diff["additional_parts"]
        }

        # 全キーのセット（reorder検出: deletional/additional以外で片方だけ空の行）
        all_source_keys: set[str] = set(source_keys)
        all_target_keys: set[str] = set(target_keys)

        # 各行のハイライトタイプを決定
        source_diff_types: list[str] = []
        target_diff_types: list[str] = []

        for src_key, tgt_key in zip(aligned_src_keys, aligned_tgt_keys):
            # source側の判定
            if src_key == "":
                source_diff_types.append("empty")
            elif src_key in deletional_key_set:
                # sourceにのみ存在（構造的削除）
                source_diff_types.append("delete")
            elif tgt_key != src_key and src_key in all_target_keys:
                # targetにも存在するが整列行でずれている → 順番違い
                source_diff_types.append("reorder")
            else:
                source_diff_types.append("equal")

            # target側の判定
            if tgt_key == "":
                target_diff_types.append("empty")
            elif tgt_key in additional_key_set:
                # targetにのみ存在（構造的追加）
                target_diff_types.append("insert")
            elif src_key != tgt_key and tgt_key in all_source_keys:
                # sourceにも存在するが整列行でずれている → 順番違い
                target_diff_types.append("reorder")
            else:
                target_diff_types.append("equal")

        return (
            aligned_source,
            aligned_target,
            source_diff_types,
            target_diff_types,
            aligned_src_keys,
            aligned_tgt_keys,
        )
