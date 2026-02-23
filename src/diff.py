import difflib
from hier_config import HConfig, Platform, get_hconfig

try:
    from src.utils import (
        calcurate_hierarcihical_path,
        remove_plus_minus_from_diff_line,
    )
except ModuleNotFoundError:
    from utils import (
        calcurate_hierarcihical_path,
        remove_plus_minus_from_diff_line,
    )

class HierarchicalDiffAnalyzer:
    def __init__(self):
        pass

    @staticmethod
    def analyze_structural_diff(source_config: HConfig, target_config: HConfig) -> dict:
        """コンフィグ構造の差分を出力する

        Args:
            source_config (HConfig): 比較元のrunning-config
            target_config (HConfig): 比較先のrunning-config
        """
        structural_diff = list(source_config.unified_diff(target_config))
        cleaned_diff = [
            remove_plus_minus_from_diff_line(line) for line in structural_diff
        ]
        structural_diff_path_list = calcurate_hierarcihical_path(cleaned_diff)
        additinal_parts_path_list = []
        deletional_parts_path_list = []
        non_changed_parts_path_list = []
        for diff_path, line in zip(structural_diff_path_list, structural_diff):
            if line.lstrip().startswith('+'):
                additinal_parts_path_list.append(diff_path)
            elif line.lstrip().startswith('-'):
                deletional_parts_path_list.append(diff_path)
            else:
                non_changed_parts_path_list.append(diff_path)
        return {
            "additional_parts": additinal_parts_path_list,
            "deletional_parts": deletional_parts_path_list,
            "non_changed_parts": non_changed_parts_path_list
        }


class TextAlignedDiffComparator:
    """2つのテキストを比較し、WinMergeのように高さを揃えるクラス"""

    @staticmethod
    def _build_hierarchical_keys(lines: list[str]) -> list[str]:
        """各行の階層パスをキーとして返す

        階層パスを使用することで、同じテキストでも異なる階層にある行を
        区別して比較できます。

        Args:
            lines (list[str]): テキストの行のリスト

        Returns:
            list[str]: 各行の階層パスを連結したキーのリスト

        Example:
            >>> lines = ["interface Gi0/0", " no shutdown"]
            >>> keys = TextAlignedDiffComparator._build_hierarchical_keys(lines)
            >>> keys[1]
            'interface Gi0/0 > no shutdown'
        """
        paths = calcurate_hierarcihical_path(lines)
        return [" > ".join(path) for path in paths]

    @staticmethod
    def _build_aligned_diff(
        source_lines: list[str],
        target_lines: list[str],
        source_keys: list[str],
        target_keys: list[str],
    ) -> tuple[list[str], list[str], list[str]]:
        """階層パスキーを使って差分を計算し、行を揃える内部メソッド

        Args:
            source_lines (list[str]): source側の表示用行リスト
            target_lines (list[str]): target側の表示用行リスト
            source_keys (list[str]): source側の比較用キーリスト
            target_keys (list[str]): target側の比較用キーリスト

        Returns:
            tuple[list[str], list[str], list[str]]: (
                source側の行リスト,
                target側の行リスト,
                差分タイプのリスト ("equal", "delete", "insert", "replace")
            )
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
        """階層パスキーを使って差分を計算し、行とキーを揃えて返す内部メソッド

        Args:
            source_lines (list[str]): source側の表示用行リスト
            target_lines (list[str]): target側の表示用行リスト
            source_keys (list[str]): source側の比較用キーリスト
            target_keys (list[str]): target側の比較用キーリスト

        Returns:
            tuple[list[str], list[str], list[str], list[str]]: (
                source側の行リスト,
                target側の行リスト,
                source側の整列後キーリスト（空行は""）,
                target側の整列後キーリスト（空行は""）
            )
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
                source_count = i2 - i1
                target_count = j2 - j1

                for i in range(i1, i2):
                    aligned_source.append(source_lines[i])
                    aligned_source_keys.append(source_keys[i])
                for j in range(j1, j2):
                    aligned_target.append(target_lines[j])
                    aligned_target_keys.append(target_keys[j])

                diff_count = abs(source_count - target_count)
                if source_count < target_count:
                    aligned_source.extend([""] * diff_count)
                    aligned_source_keys.extend([""] * diff_count)
                elif target_count < source_count:
                    aligned_target.extend([""] * diff_count)
                    aligned_target_keys.extend([""] * diff_count)

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
        source_text: str, target_text: str
    ) -> tuple[list[str], list[str]]:
        """2つのテキストを比較し、高さを揃えた行のリストを返す

        階層パスをキーとして差分を計算するため、同じテキストでも
        異なる親ブロック下にある行は別物として扱われます。

        Args:
            source_text (str): 比較元のテキスト
            target_text (str): 比較先のテキスト

        Returns:
            tuple[list[str], list[str]]: 高さを揃えた
                (source側の行リスト, target側の行リスト)

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
        source_text: str, target_text: str
    ) -> tuple[list[str], list[str], list[str]]:
        """2つのテキストを比較し、高さを揃えた行と差分情報を返す

        階層パスをキーとして差分を計算するため、同じテキストでも
        異なる親ブロック下にある行は別物として扱われます。

        Args:
            source_text (str): 比較元のテキスト
            target_text (str): 比較先のテキスト

        Returns:
            tuple[list[str], list[str], list[str]]: (
                source側の行リスト,
                target側の行リスト,
                差分タイプのリスト ("equal", "delete", "insert", "replace")
            )
        """
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
    ) -> tuple[
        list[str], list[str],
        list[str], list[str],
        list[str], list[str],
    ]:
        """構造的差分に基づき、高さを揃えた行とハイライト情報を返す

        行の整列はテキスト差分（SequenceMatcher）で行い、ハイライトの判定は
        hier_config の analyze_structural_diff に基づく構造的差分で行います。
        これにより、記載順が異なっても構造的に同一の行はハイライトされません。

        ハイライトタイプ:
            - "equal"  : 両方に存在し、順番も一致
            - "delete" : sourceにのみ存在
            - "insert" : targetにのみ存在
            - "reorder": 両方に存在するが、順番が異なる
            - "empty"  : 対応行がない側のパディング

        Args:
            source_text (str): 比較元のテキスト
            target_text (str): 比較先のテキスト
            platform (Platform): コンフィグのプラットフォーム

        Returns:
            tuple: (
                source側の行リスト,
                target側の行リスト,
                source側のハイライトタイプリスト,
                target側のハイライトタイプリスト,
                source側の整列後キーリスト,
                target側の整列後キーリスト,
            )
        """
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