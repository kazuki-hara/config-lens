"""CLI モジュール（src/cli.py）のテスト。

内部関数を直接テストする単体テストと、
subprocess 経由の統合テストを含む。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.cli import _apply_ignore, _build_parser, _format_html, _format_json, _format_text

# テスト用のフィクスチャパス
_FIXTURES = Path(__file__).parent / "fixtures"
_SOURCE = _FIXTURES / "source.txt"
_TARGET = _FIXTURES / "target.txt"


# ---------------------------------------------------------------------------
# _build_parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    """_build_parser() のテスト。"""

    def test_default_platform_is_cisco_ios(self) -> None:
        """--platform を省略したとき CISCO_IOS がデフォルト値になる。"""
        parser = _build_parser()
        args = parser.parse_args([str(_SOURCE), str(_TARGET)])
        assert args.platform == "CISCO_IOS"

    def test_default_output_is_text(self) -> None:
        """--output を省略したとき text がデフォルト値になる。"""
        parser = _build_parser()
        args = parser.parse_args([str(_SOURCE), str(_TARGET)])
        assert args.output == "text"

    def test_ignore_can_be_specified_multiple_times(self) -> None:
        """--ignore を複数回指定できることを確認する。"""
        parser = _build_parser()
        args = parser.parse_args(
            [str(_SOURCE), str(_TARGET), "--ignore", "foo", "--ignore", "bar"]
        )
        assert args.ignore == ["foo", "bar"]

    def test_output_file_is_none_by_default(self) -> None:
        """--output-file を省略したとき None になる。"""
        parser = _build_parser()
        args = parser.parse_args([str(_SOURCE), str(_TARGET)])
        assert args.output_file is None


# ---------------------------------------------------------------------------
# _apply_ignore
# ---------------------------------------------------------------------------


class TestApplyIgnore:
    """_apply_ignore() のテスト。"""

    def test_no_patterns_leaves_types_unchanged(self) -> None:
        """パターンが空のとき差分タイプは変更されない。"""
        src_types = ["delete", "equal"]
        tgt_types = ["empty", "insert"]
        _apply_ignore(["a", "b"], ["", "c"], src_types, tgt_types, [])
        assert src_types == ["delete", "equal"]
        assert tgt_types == ["empty", "insert"]

    def test_matching_line_becomes_ignore(self) -> None:
        """パターンにマッチした行の差分タイプが 'ignore' に変わる。"""
        src_types = ["delete", "equal"]
        tgt_types = ["empty", "insert"]
        _apply_ignore(
            ["ntp server 1.1.1.1", "hostname router"],
            ["", "hostname switch"],
            src_types,
            tgt_types,
            [r"ntp server"],
        )
        assert src_types[0] == "ignore"
        assert tgt_types[0] == "ignore"
        # マッチしない行は変更されない
        assert src_types[1] == "equal"

    def test_non_matching_line_is_unchanged(self) -> None:
        """パターンにマッチしない行は変更されない。"""
        src_types = ["delete"]
        tgt_types = ["empty"]
        _apply_ignore(["hostname router"], [""], src_types, tgt_types, [r"ntp"])
        assert src_types[0] == "delete"


# ---------------------------------------------------------------------------
# _format_text
# ---------------------------------------------------------------------------


class TestFormatText:
    """_format_text() のテスト。"""

    def test_no_diff_returns_no_diff_message(self) -> None:
        """差分なしのとき 差分なし メッセージを返す。"""
        result = _format_text(
            ["line1"], ["line1"], ["equal"], ["equal"]
        )
        assert "差分なし" in result

    def test_delete_line_has_minus_prefix(self) -> None:
        """delete タイプのソース行に '-' プレフィックスが付く。"""
        result = _format_text(
            ["old line"], [""], ["delete"], ["empty"]
        )
        assert result.startswith("- old line")

    def test_insert_line_has_plus_prefix(self) -> None:
        """insert タイプのターゲット行に '+' プレフィックスが付く。"""
        result = _format_text(
            [""], ["new line"], ["empty"], ["insert"]
        )
        assert result.startswith("+ new line")

    def test_reorder_lines_appear_with_both_prefixes(self) -> None:
        """reorder タイプは '-' および '+' 両方で出力される。"""
        result = _format_text(
            ["aaa"], ["bbb"], ["reorder"], ["reorder"]
        )
        assert "- aaa" in result
        assert "+ bbb" in result


# ---------------------------------------------------------------------------
# _format_json
# ---------------------------------------------------------------------------


class TestFormatJson:
    """_format_json() のテスト。"""

    def test_output_is_valid_json(self) -> None:
        """出力が有効な JSON 文字列であることを確認する。"""
        result = _format_json(
            ["a"], ["a"], ["equal"], ["equal"], "src.txt", "tgt.txt"
        )
        parsed = json.loads(result)
        assert "has_diff" in parsed
        assert "rows" in parsed

    def test_no_diff_has_diff_is_false(self) -> None:
        """差分なしのとき has_diff が False になる。"""
        result = _format_json(
            ["a"], ["a"], ["equal"], ["equal"], "src.txt", "tgt.txt"
        )
        parsed = json.loads(result)
        assert parsed["has_diff"] is False

    def test_with_diff_has_diff_is_true(self) -> None:
        """差分ありのとき has_diff が True になる。"""
        result = _format_json(
            ["old"], [""], ["delete"], ["empty"], "src.txt", "tgt.txt"
        )
        parsed = json.loads(result)
        assert parsed["has_diff"] is True

    def test_file_paths_are_included(self) -> None:
        """src_file と tgt_file が JSON に含まれる。"""
        result = _format_json(
            ["x"], ["x"], ["equal"], ["equal"], "a.txt", "b.txt"
        )
        parsed = json.loads(result)
        assert parsed["src_file"] == "a.txt"
        assert parsed["tgt_file"] == "b.txt"


# ---------------------------------------------------------------------------
# _format_html
# ---------------------------------------------------------------------------


class TestFormatHtml:
    """_format_html() のテスト。"""

    def test_output_starts_with_doctype(self) -> None:
        """出力が DOCTYPE 宣言で始まることを確認する。"""
        result = _format_html(
            ["a"], ["a"], ["equal"], ["equal"], "src.txt", "tgt.txt"
        )
        assert result.startswith("<!DOCTYPE html>")

    def test_source_and_target_paths_appear_in_html(self) -> None:
        """ソースおよびターゲットのパスが HTML 内に含まれる。"""
        result = _format_html(
            ["a"], ["a"], ["equal"], ["equal"], "src.txt", "tgt.txt"
        )
        assert "src.txt" in result
        assert "tgt.txt" in result

    def test_html_escaping_of_angle_brackets(self) -> None:
        """< と > が HTML エスケープされることを確認する。"""
        result = _format_html(
            ["<config>"], ["<config>"], ["equal"], ["equal"], "s", "t"
        )
        assert "&lt;config&gt;" in result
        assert "<config>" not in result.split("<title>")[1]


# ---------------------------------------------------------------------------
# 統合テスト（subprocess）
# ---------------------------------------------------------------------------


class TestCliIntegration:
    """subprocess 経由で main.py を呼び出して exit code を確認する統合テスト。"""

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        """main.py を subprocess で実行して結果を返す。"""
        return subprocess.run(
            [sys.executable, "main.py", *args],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

    def test_exit_code_1_when_diff_exists(self) -> None:
        """差分があるとき終了コード 1 で終了する。"""
        result = self._run(str(_SOURCE), str(_TARGET))
        assert result.returncode == 1

    def test_exit_code_0_with_identical_files(self, tmp_path) -> None:
        """同一ファイルを比較したとき終了コード 0 で終了する。"""
        same = tmp_path / "same.txt"
        same.write_text("hostname router\n", encoding="utf-8")
        result = self._run(str(same), str(same))
        assert result.returncode == 0

    def test_exit_code_2_when_file_not_found(self) -> None:
        """存在しないファイルを指定したとき終了コード 2 で終了する。"""
        result = self._run("/no/such/file.txt", str(_TARGET))
        assert result.returncode == 2

    def test_json_output_format(self) -> None:
        """--output json を指定したとき JSON 形式で出力される。"""
        result = self._run(str(_SOURCE), str(_TARGET), "--output", "json")
        parsed = json.loads(result.stdout)
        assert "has_diff" in parsed
        assert "rows" in parsed

    def test_html_output_format(self) -> None:
        """--output html を指定したとき HTML が出力される。"""
        result = self._run(str(_SOURCE), str(_TARGET), "--output", "html")
        assert "<!DOCTYPE html>" in result.stdout

    def test_ignore_flag_can_suppress_diff(self, tmp_path) -> None:
        """--ignore でマッチした行のみ異なる場合に終了コード 0 になる。"""
        src = tmp_path / "src.txt"
        tgt = tmp_path / "tgt.txt"
        # ntp server 行のみ異なる
        src.write_text("ntp server 1.1.1.1\n", encoding="utf-8")
        tgt.write_text("ntp server 2.2.2.2\n", encoding="utf-8")
        result = self._run(
            str(src), str(tgt), "--ignore", r"ntp server"
        )
        # ignore で差分が消えるため終了コード 0 になる
        assert result.returncode == 0

    def test_output_file_is_written(self, tmp_path) -> None:
        """--output-file を指定したとき、ファイルに結果が書き込まれる。"""
        out = tmp_path / "result.txt"
        self._run(
            str(_SOURCE), str(_TARGET), "--output-file", str(out)
        )
        assert out.exists()
        assert out.stat().st_size > 0
