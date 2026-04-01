"""ai_review モジュールのテスト。"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.compare.ai_review import (
    ConfigDiffReviewer,
    ReviewResult,
    _build_prompt,
    _correlate_changes,
    _parse_response,
    build_hierarchical_diff_text,
    run_review_in_background,
)


# ---------------------------------------------------------------------------
# _build_prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    """_build_prompt 関数のテスト。"""

    def test_contains_platform_name(self) -> None:
        """プロンプトにプラットフォーム名が含まれる。"""
        prompt = _build_prompt("### 追加された設定\n- router bgp 65000", "CISCO_IOS")
        assert "CISCO_IOS" in prompt

    def test_contains_diff_text(self) -> None:
        """プロンプトに差分テキストが含まれる。"""
        diff_text = "### 追加された設定\n- router bgp 65000 > neighbor 10.1.0.1 remote-as 65100"
        prompt = _build_prompt(diff_text, "CISCO_IOS")
        assert "router bgp 65000" in prompt
        assert "neighbor 10.1.0.1 remote-as 65100" in prompt


# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------


class TestParseResponse:
    """_parse_response 関数のテスト。"""

    def test_raw_markdown_preserved(self) -> None:
        """raw_markdown に値がそのまま保持される。"""
        raw = "## 変更概要\nNTP変更。\n"
        result = _parse_response(raw)
        assert result.raw_markdown == raw.strip()

    def test_whitespace_stripped(self) -> None:
        """raw_markdown の先後の空白が除去される。"""
        raw = "  ## 変更概要\n小さな変更。\n  "
        result = _parse_response(raw)
        assert not result.raw_markdown.startswith(" ")
        assert not result.raw_markdown.endswith(" ")


# ---------------------------------------------------------------------------
# ReviewResult
# ---------------------------------------------------------------------------


class TestReviewResult:
    """ReviewResult クラスのテスト。"""

    def test_attributes(self) -> None:
        """属性が正しく設定される。"""
        result = ReviewResult(raw_markdown="## 変更概要\nNTP変更。\n")
        assert "変更概要" in result.raw_markdown


# ---------------------------------------------------------------------------
# ConfigDiffReviewer.is_available
# ---------------------------------------------------------------------------


class TestConfigDiffReviewerIsAvailable:
    """ConfigDiffReviewer.is_available のテスト。"""

    def test_returns_false_when_sdk_not_installed(self) -> None:
        """apple_fm_sdk がない場合は False を返す。"""
        with patch.dict("sys.modules", {"apple_fm_sdk": None}):
            available, reason = ConfigDiffReviewer.is_available()
        assert not available
        assert "apple-fm-sdk" in reason

    def test_returns_false_when_model_unavailable(self) -> None:
        """SystemLanguageModel が利用不可の場合は False を返す。"""
        mock_model = MagicMock()
        mock_model.is_available.return_value = (False, "No Apple Intelligence")
        mock_fm = MagicMock()
        mock_fm.SystemLanguageModel.return_value = mock_model

        with patch.dict("sys.modules", {"apple_fm_sdk": mock_fm}):
            available, reason = ConfigDiffReviewer.is_available()

        assert not available
        assert "Apple Intelligence" in reason or "Foundation Models" in reason

    def test_returns_true_when_model_available(self) -> None:
        """モデルが利用可能なとき True を返す。"""
        mock_model = MagicMock()
        mock_model.is_available.return_value = (True, "")
        mock_fm = MagicMock()
        mock_fm.SystemLanguageModel.return_value = mock_model

        with patch.dict("sys.modules", {"apple_fm_sdk": mock_fm}):
            available, reason = ConfigDiffReviewer.is_available()

        assert available
        assert reason == ""


# ---------------------------------------------------------------------------
# ConfigDiffReviewer.review
# ---------------------------------------------------------------------------


class TestConfigDiffReviewerReview:
    """ConfigDiffReviewer.review のテスト。"""

    def test_review_returns_result(self) -> None:
        """review メソッドが ReviewResult を返す。"""
        mock_session = MagicMock()
        mock_session.respond = AsyncMock(
            return_value="## 変更概要\nNTP変更。"
        )
        mock_fm = MagicMock()
        mock_model = MagicMock()
        mock_model.is_available.return_value = (True, "")
        mock_fm.SystemLanguageModel.return_value = mock_model
        mock_fm.LanguageModelSession.return_value = mock_session

        reviewer = ConfigDiffReviewer()
        with patch.dict("sys.modules", {"apple_fm_sdk": mock_fm}), \
             patch("src.compare.ai_review.build_hierarchical_diff_text",
                   return_value="### 追加された設定\n- hostname router2"):
            result = asyncio.run(
                reviewer.review("hostname router\n", "hostname router2\n", "CISCO_IOS")
            )

        assert isinstance(result, ReviewResult)
        assert "NTP変更" in result.raw_markdown

    def test_review_raises_when_unavailable(self) -> None:
        """モデルが利用不可の場合に例外を送出する。"""
        with patch.dict("sys.modules", {"apple_fm_sdk": None}):
            reviewer = ConfigDiffReviewer()
            with pytest.raises((RuntimeError, ModuleNotFoundError)):
                asyncio.run(
                    reviewer.review("hostname router\n", "hostname router2\n", "CISCO_IOS")
                )


# ---------------------------------------------------------------------------
# run_review_in_background
# ---------------------------------------------------------------------------


class TestRunReviewInBackground:
    """run_review_in_background 関数のテスト。"""

    def test_calls_on_error_when_unavailable(self) -> None:
        """SDK がない場合に on_error コールバックが呼ばれる。"""
        import threading

        errors: list[str] = []
        event = threading.Event()

        def on_error(msg: str) -> None:
            errors.append(msg)
            event.set()

        # is_available をパッチしてスレッド内でも有効な状態にする
        patcher = patch(
            "src.compare.ai_review.ConfigDiffReviewer.is_available",
            return_value=(False, "Apple Intelligence が利用できません"),
        )
        patcher.start()
        try:
            run_review_in_background(
                source_text="hostname router\n",
                target_text="hostname router2\n",
                platform_name="CISCO_IOS",
                on_success=lambda _: None,
                on_error=on_error,
            )
            event.wait(timeout=5)
        finally:
            patcher.stop()

        assert len(errors) == 1


# ---------------------------------------------------------------------------
# build_hierarchical_diff_text
# ---------------------------------------------------------------------------


class TestBuildHierarchicalDiffText:
    """build_hierarchical_diff_text 関数のテスト。"""

    _BASE = "hostname router\n"

    def test_returns_no_diff_message_when_identical(self) -> None:
        """差分がない場合は (no diff) を返す。"""
        result = build_hierarchical_diff_text(self._BASE, self._BASE, "CISCO_IOS")
        assert "(no diff)" in result

    def test_addition_appears_in_output(self) -> None:
        """追加設定が ADDED セクションに出力される。"""
        source = "hostname router\n"
        target = (
            "hostname router\n"
            "router bgp 65000\n"
            " neighbor 10.1.0.1 remote-as 65100\n"
        )
        result = build_hierarchical_diff_text(source, target, "CISCO_IOS")
        assert "ADDED" in result
        assert "router bgp 65000" in result

    def test_deletion_appears_in_output(self) -> None:
        """削除設定が REMOVED セクションに出力される。"""
        source = (
            "hostname router\n"
            "router bgp 65000\n"
            " neighbor 10.1.0.1 remote-as 65100\n"
        )
        target = "hostname router\n"
        result = build_hierarchical_diff_text(source, target, "CISCO_IOS")
        assert "REMOVED" in result
        assert "router bgp 65000" in result

    def test_modification_detected(self) -> None:
        """同一インタフェース下の ip address 変更が MODIFIED セクションに出力される。"""
        source = (
            "hostname router\n"
            "interface GigabitEthernet0/0\n"
            " ip address 192.168.1.1 255.255.255.0\n"
        )
        target = (
            "hostname router\n"
            "interface GigabitEthernet0/0\n"
            " ip address 10.0.0.1 255.255.255.0\n"
        )
        result = build_hierarchical_diff_text(source, target, "CISCO_IOS")
        assert "MODIFIED" in result
        assert "\u2192" in result  # →
        assert "192.168.1.1" in result
        assert "10.0.0.1" in result

    def test_hierarchical_path_format(self) -> None:
        """出力が「親 > 子」の層次形式で記載される。"""
        source = "hostname router\n"
        target = (
            "hostname router\n"
            "router bgp 65000\n"
            " neighbor 10.1.0.1 remote-as 65100\n"
        )
        result = build_hierarchical_diff_text(source, target, "CISCO_IOS")
        # 子設定は親ブロックのパスを含む形式で出力される
        assert ">" in result

    def test_unsupported_platform_returns_message(self) -> None:
        """未対応プラットフォームの場合はエラーメッセージを返す。"""
        result = build_hierarchical_diff_text(self._BASE, self._BASE, "UNKNOWN_PLATFORM")
        assert "未対応" in result


# ---------------------------------------------------------------------------
# _correlate_changes
# ---------------------------------------------------------------------------


class TestCorrelateChanges:
    """_correlate_changes 関数のテスト。"""

    def test_matches_same_parent_and_keyword(self) -> None:
        """同じ親パスかつ同じコマンドキーワードを持つ追加・削除ペアが変更として検出される。"""
        deletions = [["interface GigabitEthernet0/0", "ip address 192.168.1.1 255.255.255.0"]]
        additions = [["interface GigabitEthernet0/0", "ip address 10.0.0.1 255.255.255.0"]]
        modifications, pure_add, pure_del = _correlate_changes(additions, deletions)
        assert len(modifications) == 1
        assert modifications[0][0] == deletions[0]
        assert modifications[0][1] == additions[0]
        assert pure_add == []
        assert pure_del == []

    def test_different_parent_stays_separate(self) -> None:
        """親パスが異なる場合はペアにならない。"""
        deletions = [["interface GigabitEthernet0/0", "ip address 192.168.1.1 255.255.255.0"]]
        additions = [["interface GigabitEthernet0/1", "ip address 10.0.0.1 255.255.255.0"]]
        modifications, pure_add, pure_del = _correlate_changes(additions, deletions)
        assert len(modifications) == 0
        assert pure_add == additions
        assert pure_del == deletions

    def test_different_keyword_stays_separate(self) -> None:
        """コマンドキーワードが異なる場合はペアにならない。"""
        deletions = [["interface GigabitEthernet0/0", "ip address 192.168.1.1 255.255.255.0"]]
        additions = [["interface GigabitEthernet0/0", "shutdown"]]
        modifications, pure_add, pure_del = _correlate_changes(additions, deletions)
        assert len(modifications) == 0
        assert pure_add == additions
        assert pure_del == deletions

    def test_empty_inputs(self) -> None:
        """追加・削除が空の場合は空リストを返す。"""
        modifications, pure_add, pure_del = _correlate_changes([], [])
        assert modifications == []
        assert pure_add == []
        assert pure_del == []

    def test_pure_addition_only(self) -> None:
        """追加のみの場合は純追加として残る。"""
        additions = [["router bgp 65000", "neighbor 10.1.0.1 remote-as 65100"]]
        modifications, pure_add, pure_del = _correlate_changes(additions, [])
        assert modifications == []
        assert pure_add == additions
        assert pure_del == []

