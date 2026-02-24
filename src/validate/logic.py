"""Config Validator のロジックモジュール。

現在のrunning-config・設定変更内容・想定されるrunning-configの
3入力を受け取り、構造的差分解析によって各差分が設定変更内容に
起因するかどうかを検証する。

差分の計算は CompareView と同じ TextAlignedDiffComparator を流用し、
設定変更内容との照合には階層パスキーを使用する。
"""

from dataclasses import dataclass, field

from hier_config import Platform

from src.compare.logic import TextAlignedDiffComparator
from src.utils import calculate_hierarchical_path


@dataclass
class ValidateResult:
    """検証結果データクラス。

    Attributes:
        running_lines: 整列後の running-config 表示用行リスト
        expected_lines: 整列後の expected running-config 表示用行リスト
        change_lines: 設定変更内容の生行リスト
        running_types: running_lines の各行タイプ
            ``"equal"`` / ``"change_remove"`` / ``"remove"`` /
            ``"reorder"`` / ``"empty"``
        expected_types: expected_lines の各行タイプ
            ``"equal"`` / ``"change_add"`` / ``"add"`` /
            ``"reorder"`` / ``"empty"``
        change_types: change_lines の各行タイプ
            ``"normal"`` / ``"change"``（設定変更差分に対応する行）/
            ``"unmatched"``（意味ある変更コマンドだが差分に現れない = 想定漏れ）
        change_to_running: change行インデックス → running列行番号リスト（1ベース）
        change_to_expected: change行インデックス → expected列行番号リスト（1ベース）
        is_valid: 全差分が設定変更内容由来かどうか
        has_unapplied_change: 設定変更内容に想定漏れ（差分に現れないコマンド）があるか
    """

    running_lines: list[str]
    expected_lines: list[str]
    change_lines: list[str]
    running_types: list[str]
    expected_types: list[str]
    change_types: list[str]
    change_to_running: dict[int, list[int]] = field(default_factory=dict)
    change_to_expected: dict[int, list[int]] = field(default_factory=dict)
    is_valid: bool = True
    has_unapplied_change: bool = False


def _build_change_key_maps(
    change_lines: list[str],
) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    """設定変更内容の各行から階層パスキーマップを構築する。

    各 change 行を以下の対称ルールで両マップに登録する。

    - ``no X`` の場合:
        - remove_key_map: 葉ノードから ``no `` を除いたキー
          （running に ``X`` が存在し削除されることを照合）
        - add_key_map: ``no X`` そのままのキー
          （expected に ``no X`` が追加されることを照合）
    - ``Y``（no なし）の場合:
        - remove_key_map: 葉ノードに ``no `` を付加したキー
          （running に ``no Y`` が存在し削除されることを照合）
        - add_key_map: ``Y`` そのままのキー
          （expected に ``Y`` が追加されることを照合）

    ``no interface X`` のようなブロック削除の場合、子行も同じ change 行
    インデックスにマッピングされるよう、後段の検索でプレフィックス照合される。

    Args:
        change_lines: 設定変更内容の行リスト

    Returns:
        ``(add_key_map, remove_key_map)`` のタプル。

        - add_key_map: 階層パスキー → change行インデックスリスト（追加系照合用）
        - remove_key_map: 階層パスキー → change行インデックスリスト（削除系照合用）
    """
    paths = calculate_hierarchical_path(change_lines)
    add_key_map: dict[str, list[int]] = {}
    remove_key_map: dict[str, list[int]] = {}

    for ci, (line, path) in enumerate(zip(change_lines, paths)):
        stripped = line.strip()
        if not stripped or stripped.startswith("!"):
            continue

        if stripped.startswith("no "):
            leaf_without_no = stripped[3:].strip()
            # remove_key: noを除いた葉ノード（running の削除行と照合）
            remove_path = path[:-1] + [leaf_without_no]
            remove_key_map.setdefault(
                " > ".join(remove_path), []
            ).append(ci)
            # add_key: no X そのまま（expected の追加行と照合）
            add_key_map.setdefault(
                " > ".join(path), []
            ).append(ci)
        else:
            # add_key: Y そのまま（expected の追加行と照合）
            add_key_map.setdefault(
                " > ".join(path), []
            ).append(ci)
            # remove_key: no Y（running の削除行と照合）
            leaf_with_no = "no " + stripped
            remove_path_no = path[:-1] + [leaf_with_no]
            remove_key_map.setdefault(
                " > ".join(remove_path_no), []
            ).append(ci)

    return add_key_map, remove_key_map


def validate(
    running_text: str,
    change_text: str,
    expected_text: str,
    platform: Platform,
) -> ValidateResult:
    """3つのコンフィグテキストを構造的差分で検証する。

    1. ``TextAlignedDiffComparator`` で running ↔ expected の
       構造的差分（階層パスキーベース）を計算する。
    2. 設定変更内容のノーコマンドを解析して
       add_key_map / remove_key_map を構築する。
    3. 各差分行の階層パスキーを変更内容のキーと照合し、
       由来が明確な差分は ``change_remove`` / ``change_add`` に、
       説明できない差分は ``remove`` / ``add`` （検証エラー）に分類する。

    Args:
        running_text: 現在のrunning-configのテキスト全体
        change_text: 設定変更内容のテキスト全体
        expected_text: 想定されるrunning-configのテキスト全体
        platform: コンフィグのプラットフォーム（hier_config に渡す）

    Returns:
        ValidateResult: 検証結果
    """
    change_lines = change_text.splitlines()

    # running ↔ expected の構造的差分（CompareView と同じロジック）
    (
        running_lines,
        expected_lines,
        raw_running_types,
        raw_expected_types,
        running_keys,
        expected_keys,
    ) = TextAlignedDiffComparator.compare_and_align_with_structural_diff_info(
        running_text, expected_text, platform
    )

    # 設定変更内容のキーマップを構築
    add_key_map, remove_key_map = _build_change_key_maps(change_lines)

    # remove_key をここで小文字化してプレフィックス照合用セットを作成
    # キー: 小文字remove_key, 値: (original_remove_key, ci_list)
    lower_remove_entries: list[tuple[str, list[int]]] = [
        (rk.lower(), cis) for rk, cis in remove_key_map.items()
    ]

    # change行のタイプと対応行マップを初期化
    change_types: list[str] = ["normal"] * len(change_lines)
    change_to_running: dict[int, list[int]] = {}
    change_to_expected: dict[int, list[int]] = {}
    has_error = False

    final_running_types: list[str] = []
    final_expected_types: list[str] = []

    for display_row, (src_key, tgt_key, src_type, tgt_type) in enumerate(
        zip(running_keys, expected_keys, raw_running_types, raw_expected_types),
        start=1,
    ):
        # running 列の判定
        if src_type == "delete":
            # 直接照合（正規化済みキー同士）
            ci_list = remove_key_map.get(src_key, [])
            if not ci_list:
                # プレフィックス照合（no interface X → 子行もマッチ）
                src_key_lower = src_key.lower()
                for rk_lower, cis in lower_remove_entries:
                    if src_key_lower == rk_lower or src_key_lower.startswith(
                        rk_lower + " > "
                    ):
                        ci_list = cis
                        break
            if ci_list:
                final_running_types.append("change_remove")
                for ci in ci_list:
                    change_types[ci] = "change"
                    change_to_running.setdefault(ci, []).append(display_row)
            else:
                final_running_types.append("remove")
                has_error = True
        else:
            final_running_types.append(src_type)

        # expected 列の判定
        if tgt_type == "insert":
            ci_list = add_key_map.get(tgt_key, [])
            if ci_list:
                final_expected_types.append("change_add")
                for ci in ci_list:
                    change_types[ci] = "change"
                    change_to_expected.setdefault(ci, []).append(display_row)
            else:
                final_expected_types.append("add")
                has_error = True
        else:
            final_expected_types.append(tgt_type)

    # 照合済み ci の階層パスの祖先キーを収集（親ブロック行の誤検知防止）
    paths = calculate_hierarchical_path(change_lines)
    covered_ancestor_keys: set[str] = set()
    for ci, path in enumerate(paths):
        if change_types[ci] == "change":
            # 自行より上の全祖先キーを covered に追加
            for depth in range(1, len(path)):
                covered_ancestor_keys.add(" > ".join(path[:depth]))

    # 意味のある change 行で未対応かつ祖先でもない行を "unmatched" にマーク
    has_unapplied = False
    for ci, (line, path) in enumerate(zip(change_lines, paths)):
        stripped = line.strip()
        if stripped and not stripped.startswith("!"):
            if change_types[ci] == "normal":
                ci_key = " > ".join(path)
                if ci_key not in covered_ancestor_keys:
                    change_types[ci] = "unmatched"
                    has_unapplied = True

    return ValidateResult(
        running_lines=running_lines,
        expected_lines=expected_lines,
        change_lines=change_lines,
        running_types=final_running_types,
        expected_types=final_expected_types,
        change_types=change_types,
        change_to_running=change_to_running,
        change_to_expected=change_to_expected,
        is_valid=not has_error,
        has_unapplied_change=has_unapplied,
    )
