"""CLI エントリーポイントモジュール。

2 つのコンフィグファイルを比較し、差分をターミナルまたはファイルに出力する。

Exit codes:
    0: 差分なし
    1: 差分あり
    2: 引数エラー / 例外

Usage:
    config-lens <src> <tgt> [options]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from src.compare.logic import TextAlignedDiffComparator
from src.compare.platforms import PLATFORM_MAP

# バージョン文字列
try:
    import importlib.metadata

    _VERSION = importlib.metadata.version("01-config-lens")
except Exception:
    _VERSION = "0.3.0"

_EXIT_NO_DIFF = 0
_EXIT_DIFF = 1
_EXIT_ERROR = 2


def _build_parser() -> argparse.ArgumentParser:
    """CLI 引数パーサーを構築する。

    Returns:
        設定済みの ArgumentParser インスタンス
    """
    parser = argparse.ArgumentParser(
        prog="config-lens",
        description=(
            "ネットワーク機器のコンフィグファイルを比較してテキスト差分を出力する。"
        ),
    )
    parser.add_argument("src", help="ソースファイルのパス")
    parser.add_argument("tgt", help="ターゲットファイルのパス")
    parser.add_argument(
        "--platform",
        default="CISCO_IOS",
        choices=list(PLATFORM_MAP.keys()),
        help="プラットフォーム名（デフォルト: CISCO_IOS）",
    )
    parser.add_argument(
        "--output",
        default="text",
        choices=["text", "html", "json"],
        help="出力形式（デフォルト: text）",
    )
    parser.add_argument(
        "--output-file",
        metavar="PATH",
        help="出力先ファイルパス（省略時は stdout）",
    )
    parser.add_argument(
        "--ignore",
        metavar="REGEX",
        action="append",
        default=[],
        help="無視する行の正規表現パターン（複数回指定可）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"config-lens {_VERSION}",
    )
    return parser


def _apply_ignore(
    source_lines: list[str],
    target_lines: list[str],
    src_types: list[str],
    tgt_types: list[str],
    patterns: list[str],
) -> None:
    """Ignore パターンにマッチする行の差分タイプを 'ignore' に変更する。

    Args:
        source_lines: ソース行のリスト
        target_lines: ターゲット行のリスト
        src_types: ソース行の差分タイプリスト（インプレース更新）
        tgt_types: ターゲット行の差分タイプリスト（インプレース更新）
        patterns: 正規表現パターン文字列のリスト
    """
    if not patterns:
        return
    compiled = [re.compile(p) for p in patterns]
    for i, (sl, tl) in enumerate(zip(source_lines, target_lines)):
        line = sl if sl else tl
        if any(pat.search(line) for pat in compiled):
            src_types[i] = "ignore"
            tgt_types[i] = "ignore"


def _format_text(
    source_lines: list[str],
    target_lines: list[str],
    src_types: list[str],
    tgt_types: list[str],
) -> str:
    """差分をテキスト形式にフォーマットする。

    差分がある行のみ出力する（ソース側は '-' プレフィックス、ターゲット側は '+' プレフィックス）。

    Args:
        source_lines: ソース行のリスト
        target_lines: ターゲット行のリスト
        src_types: ソース行の差分タイプリスト
        tgt_types: ターゲット行の差分タイプリスト

    Returns:
        テキスト形式の差分文字列
    """
    lines: list[str] = []
    for sl, tl, st, tt in zip(
        source_lines, target_lines, src_types, tgt_types
    ):
        if st in ("delete", "reorder") and sl:
            lines.append(f"- {sl}")
        if tt in ("insert", "reorder") and tl:
            lines.append(f"+ {tl}")
    if not lines:
        return "(差分なし)\n"
    return "\n".join(lines) + "\n"


def _format_json(
    source_lines: list[str],
    target_lines: list[str],
    src_types: list[str],
    tgt_types: list[str],
    src_path: str,
    tgt_path: str,
) -> str:
    """差分を JSON 形式にフォーマットする。

    Args:
        source_lines: ソース行のリスト
        target_lines: ターゲット行のリスト
        src_types: ソース行の差分タイプリスト
        tgt_types: ターゲット行の差分タイプリスト
        src_path: ソースファイルのパス文字列
        tgt_path: ターゲットファイルのパス文字列

    Returns:
        JSON 形式の文字列
    """
    has_diff = any(
        t not in ("equal", "ignore", "empty")
        for t in src_types + tgt_types
    )
    rows = [
        {
            "line": i + 1,
            "src_line": sl,
            "tgt_line": tl,
            "src_type": st,
            "tgt_type": tt,
        }
        for i, (sl, tl, st, tt) in enumerate(
            zip(source_lines, target_lines, src_types, tgt_types)
        )
    ]
    payload = {
        "src_file": src_path,
        "tgt_file": tgt_path,
        "has_diff": has_diff,
        "rows": rows,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _format_html(
    source_lines: list[str],
    target_lines: list[str],
    src_types: list[str],
    tgt_types: list[str],
    src_path: str,
    tgt_path: str,
) -> str:
    """差分を HTML 形式にフォーマットする。

    インライン CSS 付きの 2 カラムテーブルを生成する。

    Args:
        source_lines: ソース行のリスト
        target_lines: ターゲット行のリスト
        src_types: ソース行の差分タイプリスト
        tgt_types: ターゲット行の差分タイプリスト
        src_path: ソースファイルのパス文字列
        tgt_path: ターゲットファイルのパス文字列

    Returns:
        HTML 形式の文字列
    """
    css_map = {
        "delete": "background:#5a1e1e;color:#ffaaaa",
        "insert": "background:#1e5a24;color:#aaffaa",
        "reorder": "background:#4d4020;color:#ffd966",
        "ignore": "background:#2f2f2f;color:#5a5a5a",
        "empty": "background:#1a1a1a",
        "equal": "",
    }

    def _esc(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    rows_html = []
    for i, (sl, tl, st, tt) in enumerate(
        zip(source_lines, target_lines, src_types, tgt_types), start=1
    ):
        src_style = css_map.get(st, "")
        tgt_style = css_map.get(tt, "")
        rows_html.append(
            f"  <tr>"
            f'<td style="width:3em;text-align:right;padding:0 4px;'
            f'color:#888">{i}</td>'
            f'<td style="font-family:monospace;{src_style};'
            f'padding:0 6px">{_esc(sl)}</td>'
            f'<td style="font-family:monospace;{tgt_style};'
            f'padding:0 6px">{_esc(tl)}</td>'
            f"</tr>"
        )

    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset='utf-8'>\n"
        f"<title>Config Diff: {_esc(src_path)} vs {_esc(tgt_path)}</title>\n"
        "<style>body{{background:#1e1e1e;color:#fff;font-family:sans-serif}}"
        "table{{border-collapse:collapse;width:100%}}"
        "th{{background:#333;padding:4px 8px;text-align:left}}"
        "td{{border-bottom:1px solid #333}}</style>\n"
        "</head><body>\n"
        f"<h2>Source: {_esc(src_path)}</h2>\n"
        f"<h2>Target: {_esc(tgt_path)}</h2>\n"
        "<table>\n"
        "<thead><tr>"
        "<th>#</th>"
        f"<th>Source: {_esc(src_path)}</th>"
        f"<th>Target: {_esc(tgt_path)}</th>"
        "</tr></thead>\n"
        "<tbody>\n"
        + "\n".join(rows_html)
        + "\n</tbody></table>\n</body></html>\n"
    )


def cli_main() -> None:
    """CLI のエントリーポイント。

    引数を解析して比較を実行し、指定された形式で出力する。
    差分の有無に応じた終了コードで終了する。
    """
    parser = _build_parser()
    # 引数なしの場合は GUI に委譲する（main.py から呼ばれる）
    if len(sys.argv) == 1:
        return

    args = parser.parse_args()

    src_path = Path(args.src)
    tgt_path = Path(args.tgt)

    if not src_path.is_file():
        print(
            f"エラー: ソースファイルが存在しません: {src_path}",
            file=sys.stderr,
        )
        sys.exit(_EXIT_ERROR)
    if not tgt_path.is_file():
        print(
            f"エラー: ターゲットファイルが存在しません: {tgt_path}",
            file=sys.stderr,
        )
        sys.exit(_EXIT_ERROR)

    try:
        src_text = src_path.read_text(encoding="utf-8")
        tgt_text = tgt_path.read_text(encoding="utf-8")
        platform = PLATFORM_MAP[args.platform]

        (
            source_lines,
            target_lines,
            src_types,
            tgt_types,
            _src_keys,
            _tgt_keys,
        ) = TextAlignedDiffComparator.compare_and_align_with_structural_diff_info(
            src_text, tgt_text, platform, normalize=True
        )

        _apply_ignore(
            source_lines, target_lines, src_types, tgt_types, args.ignore
        )

        fmt = args.output
        if fmt == "json":
            output = _format_json(
                source_lines,
                target_lines,
                src_types,
                tgt_types,
                str(src_path),
                str(tgt_path),
            )
        elif fmt == "html":
            output = _format_html(
                source_lines,
                target_lines,
                src_types,
                tgt_types,
                str(src_path),
                str(tgt_path),
            )
        else:
            output = _format_text(
                source_lines, target_lines, src_types, tgt_types
            )

        if args.output_file:
            Path(args.output_file).write_text(output, encoding="utf-8")
            print(f"出力先: {args.output_file}", file=sys.stderr)
        else:
            sys.stdout.write(output)

        # 終了コード判定
        has_diff = any(
            t not in ("equal", "ignore", "empty")
            for t in src_types + tgt_types
        )
        sys.exit(_EXIT_DIFF if has_diff else _EXIT_NO_DIFF)

    except Exception as e:
        print(f"エラー: {e!s}", file=sys.stderr)
        sys.exit(_EXIT_ERROR)
