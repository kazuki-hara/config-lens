"""AI レビューモジュール。

Apple Foundation Models SDK を使用して、コンフィグ差分の
AI レビューを提供する。macOS 26 以上 + Apple Intelligence が必要。
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable

_MAX_DIFF_LINES = 500

_SYSTEM_PROMPT = (
    "You are a network engineer specializing in enterprise network configuration.\n"
    "You will receive a structured configuration diff with three sections:\n"
    "  - MODIFIED: settings where a value changed (shown as 'old → new')\n"
    "  - ADDED: newly added settings\n"
    "  - REMOVED: deleted settings\n"
    "Each entry uses the format 'parent block > child setting'.\n"
    "\n"
    "Summarize what changed in plain, human-readable Japanese (日本語).\n"
    "Do NOT just repeat the raw diff lines.\n"
    "Instead, explain the meaning of each change "
    "(e.g. 'GigabitEthernet0/0 の IP アドレスを 192.168.1.1 から 10.0.0.1 に変更した').\n"
    "Format your response in Markdown.\n"
)


def _correlate_changes(
    additions: list[list[str]],
    deletions: list[list[str]],
) -> tuple[list[tuple[list[str], list[str]]], list[list[str]], list[list[str]]]:
    """追加・削除リストから変更（修正）ペアを相関付ける。

    同じ親パスかつ同じコマンドキーワード（先頭 2 語）を持つ追加・削除ペアを
    「変更」として検出する。例えば同一インタフェース下の ``ip address`` が
    旧値→新値に書き換わった場合、削除+追加ではなく変更として扱う。

    Args:
        additions: ``analyze_structural_diff`` の ``additional_parts``
        deletions: ``analyze_structural_diff`` の ``deletional_parts``

    Returns:
        タプル ``(変更ペアリスト, 純追加リスト, 純削除リスト)``。
        変更ペアは ``(del_path, add_path)`` のタプル。
    """

    def _key(path: list[str]) -> tuple[tuple[str, ...], str]:
        parent = tuple(path[:-1])
        last = path[-1] if path else ""
        words = last.split()
        # 先頭 2 語をコマンドキーワードとして使う ("ip address", "neighbor" など)
        keyword = " ".join(words[:2]) if len(words) >= 2 else last
        return parent, keyword

    # 削除パスをキーでインデックス化
    del_index: dict[tuple[tuple[str, ...], str], list[int]] = {}
    for i, path in enumerate(deletions):
        del_index.setdefault(_key(path), []).append(i)

    modifications: list[tuple[list[str], list[str]]] = []
    used_del: set[int] = set()
    used_add: set[int] = set()

    for j, add_path in enumerate(additions):
        key = _key(add_path)
        for i in del_index.get(key, []):
            if i not in used_del:
                modifications.append((deletions[i], add_path))
                used_del.add(i)
                used_add.add(j)
                break

    pure_additions = [p for j, p in enumerate(additions) if j not in used_add]
    pure_deletions = [p for i, p in enumerate(deletions) if i not in used_del]
    return modifications, pure_additions, pure_deletions


def build_hierarchical_diff_text(
    source_text: str,
    target_text: str,
    platform_name: str,
) -> str:
    """階層構造付きコンフィグ差分テキストを生成する。

    HierarchicalDiffAnalyzer で追加・削除を取得し、_correlate_changes で
    「同じ親ブロック下の同じコマンドキーワード」な削除+追加を「変更（旧値→新値）」
    に変換する。純追加・純削除は別セクションとして列挙する。

    Args:
        source_text: 比較元のコンフィグテキスト
        target_text: 比較先のコンフィグテキスト
        platform_name: プラットフォーム名（PLATFORM_MAP のキー）

    Returns:
        AI への入力用に整形された差分テキスト
    """
    from hier_config import get_hconfig  # noqa: PLC0415
    from src.compare.logic import HierarchicalDiffAnalyzer  # noqa: PLC0415
    from src.compare.platforms import PLATFORM_MAP  # noqa: PLC0415

    platform = PLATFORM_MAP.get(platform_name)
    if platform is None:
        return f"（未対応のプラットフォーム: {platform_name}）"

    source_hconfig = get_hconfig(platform, source_text)
    target_hconfig = get_hconfig(platform, target_text)

    diff = HierarchicalDiffAnalyzer.analyze_structural_diff(
        source_hconfig, target_hconfig
    )

    modifications, pure_additions, pure_deletions = _correlate_changes(
        diff["additional_parts"], diff["deletional_parts"]
    )

    lines: list[str] = []
    max_per_section = _MAX_DIFF_LINES // 3

    if modifications:
        lines.append("### MODIFIED")
        for del_path, add_path in modifications[:max_per_section]:
            parent = " > ".join(del_path[:-1])
            old_val = del_path[-1] if del_path else ""
            new_val = add_path[-1] if add_path else ""
            prefix = f"{parent} > " if parent else ""
            lines.append(f"- {prefix}{old_val} → {new_val}")
        if len(modifications) > max_per_section:
            lines.append(f"- (and {len(modifications) - max_per_section} more)")
        lines.append("")

    if pure_additions:
        lines.append("### ADDED")
        for path in pure_additions[:max_per_section]:
            lines.append("- " + " > ".join(path))
        if len(pure_additions) > max_per_section:
            lines.append(f"- (and {len(pure_additions) - max_per_section} more)")
        lines.append("")

    if pure_deletions:
        lines.append("### REMOVED")
        for path in pure_deletions[:max_per_section]:
            lines.append("- " + " > ".join(path))
        if len(pure_deletions) > max_per_section:
            lines.append(f"- (and {len(pure_deletions) - max_per_section} more)")
        lines.append("")

    if not lines:
        return "(no diff)"

    return "\n".join(lines)


def _build_prompt(diff_text: str, platform_name: str) -> str:
    """差分テキストからレビュー用プロンプトを構築する。

    Args:
        diff_text: 整形済みの差分テキスト（build_hierarchical_diff_text の出力）
        platform_name: プラットフォーム名

    Returns:
        AIへ渡すプロンプト文字列
    """
    return (
        f"Platform: {platform_name}\n\n"
        "Below is a structured configuration diff.\n"
        "- MODIFIED: a value was changed (shown as 'old → new')\n"
        "- ADDED: a new setting was added\n"
        "- REMOVED: an existing setting was deleted\n\n"
        "Explain each change in plain Japanese, like a human engineer would describe it.\n"
        "Do NOT just copy the raw lines. Write natural sentences or concise bullet points.\n\n"
        f"{diff_text}"
    )


class ReviewResult:
    """AIレビューの結果を保持するデータクラス。

    Attributes:
        raw_markdown: AI が生成した Markdown 形式の全レビューテキスト
    """

    def __init__(self, raw_markdown: str) -> None:
        """初期化。

        Args:
            raw_markdown: AI が生成した Markdown 全文
        """
        self.raw_markdown = raw_markdown


class ConfigDiffReviewer:
    """コンフィグ差分を AI でレビューするクラス。

    Apple Foundation Models SDK の LanguageModelSession を使用して
    差分テキストをレビューし、ReviewResult を返す。
    """

    @staticmethod
    def is_available() -> tuple[bool, str]:
        """Foundation Models が利用可能かチェックする。

        Returns:
            タプル ``(利用可能フラグ, 理由メッセージ)``
        """
        try:
            import apple_fm_sdk as fm  # type: ignore[import-untyped]
        except ImportError:
            return (
                False,
                "apple-fm-sdk がインストールされていません。",
            )

        model = fm.SystemLanguageModel()
        available, reason = model.is_available()
        if not available:
            return (
                False,
                f"Foundation Models が利用できません: {reason}\n"
                "macOS 26 以上で Apple Intelligence を有効にしてください。",
            )
        return True, ""

    async def review(
        self,
        source_text: str,
        target_text: str,
        platform_name: str,
    ) -> ReviewResult:
        """コンフィグ差分を AI にレビューさせ、結果を返す。

        Args:
            source_text: 比較元のコンフィグテキスト
            target_text: 比較先のコンフィグテキスト
            platform_name: プラットフォーム名

        Returns:
            AIレビュー結果

        Raises:
            RuntimeError: Foundation Models が利用できない場合
        """
        import apple_fm_sdk as fm  # type: ignore[import-untyped]

        available, reason = self.is_available()
        if not available:
            raise RuntimeError(reason)

        diff_text = build_hierarchical_diff_text(
            source_text, target_text, platform_name
        )
        prompt = _build_prompt(diff_text, platform_name)

        # model を明示的に生成して渡す（バックグラウンドスレッドでも
        # ロケールコンテキストが正しく参照されるようにするため）
        model = fm.SystemLanguageModel()
        session = fm.LanguageModelSession(
            instructions=_SYSTEM_PROMPT,
            model=model,
        )
        try:
            response = await session.respond(prompt)
        except fm.UnsupportedLanguageOrLocaleError as exc:
            raise RuntimeError(
                "Apple Intelligence が現在の言語・ロケール設定をサポートしていません。\n"
                "System Settings → General → Language & Region で\n"
                "Apple Intelligence に対応した言語（英語など）を追加してください。\n"
                f"（詳細: {exc}）"
            ) from exc
        raw_text: str = str(response)

        return _parse_response(raw_text)


def _parse_response(raw_text: str) -> ReviewResult:
    """AI の応答 Markdown から ReviewResult を生成する。

    Args:
        raw_text: AI から返却された応答テキスト

    Returns:
        パース済みの ReviewResult
    """
    return ReviewResult(raw_markdown=raw_text.strip())


def run_review_in_background(
    source_text: str,
    target_text: str,
    platform_name: str,
    on_success: Callable[[ReviewResult], None],
    on_error: Callable[[str], None],
) -> None:
    """バックグラウンドスレッドで AI レビューを実行する。

    Tkinter のメインスレッドと分離するために別スレッドを使用する。
    結果は ``on_success`` / ``on_error`` コールバックで通知される。
    コールバックは ``self.after(0, callback)`` 経由でUIスレッドに渡すこと。

    Args:
        source_text: 比較元のコンフィグテキスト
        target_text: 比較先のコンフィグテキスト
        platform_name: プラットフォーム名
        on_success: 成功時コールバック（ReviewResult を受け取る）
        on_error: エラー時コールバック（エラーメッセージを受け取る）
    """

    reviewer = ConfigDiffReviewer()

    def _worker() -> None:
        try:
            result = asyncio.run(
                reviewer.review(source_text, target_text, platform_name)
            )
            on_success(result)
        except Exception as exc:
            on_error(str(exc))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
