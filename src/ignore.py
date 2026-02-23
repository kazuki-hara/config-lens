"""Ignoreパターンを管理するモジュール。

パターンはOS標準のユーザーデータディレクトリに JSON 形式で保存される。
  macOS : ~/Library/Application Support/ConfigLens/ignore_patterns.json
  Windows: %APPDATA%/ConfigLens/ignore_patterns.json
  Linux  : ~/.local/share/ConfigLens/ignore_patterns.json
"""

import json
import re
from pathlib import Path

from platformdirs import user_data_dir

_SETTINGS_DIR: Path = Path(user_data_dir(appname="ConfigLens", appauthor=False))
_SETTINGS_FILE: Path = _SETTINGS_DIR / "ignore_patterns.json"


class IgnorePatternManager:
    """Ignore対象の正規表現パターンを管理するクラス。

    パターンはOS標準のユーザーデータディレクトリに保存され、
    アプリ再起動後も維持される。
    """

    def __init__(self) -> None:
        self._patterns: list[str] = []
        self._compiled: list[re.Pattern[str]] = []
        self._load()

    # ------------------------------------------------------------------
    # 永続化
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """設定ファイルからパターンを読み込む。"""
        if not _SETTINGS_FILE.exists():
            return
        try:
            data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            raw: list[str] = [p for p in data.get("patterns", []) if isinstance(p, str)]
            compiled: list[re.Pattern[str]] = []
            valid: list[str] = []
            for p in raw:
                try:
                    compiled.append(re.compile(p))
                    valid.append(p)
                except re.error:
                    pass  # 無効なパターンは読み飛ばす
            self._patterns = valid
            self._compiled = compiled
        except (json.JSONDecodeError, OSError):
            self._patterns = []
            self._compiled = []

    def _save(self) -> None:
        """パターンを設定ファイルに保存する。"""
        _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        _SETTINGS_FILE.write_text(
            json.dumps({"patterns": self._patterns}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # パターン操作
    # ------------------------------------------------------------------

    def get_patterns(self) -> list[str]:
        """登録済みパターンのリストを返す（コピー）。"""
        return list(self._patterns)

    def add_pattern(self, pattern: str) -> None:
        """パターンを追加して保存する。

        Args:
            pattern: 追加する正規表現文字列（前後の空白は除去される）

        Raises:
            ValueError: 空文字列または重複パターンの場合
            re.error: 無効な正規表現の場合
        """
        pattern = pattern.strip()
        if not pattern:
            raise ValueError("パターンが空です")
        if pattern in self._patterns:
            raise ValueError(f"'{pattern}' は既に登録されています")
        compiled = re.compile(pattern)  # 無効な正規表現は re.error を送出
        self._patterns.append(pattern)
        self._compiled.append(compiled)
        self._save()

    def remove_pattern(self, pattern: str) -> None:
        """パターンを削除して保存する。"""
        if pattern in self._patterns:
            idx = self._patterns.index(pattern)
            self._patterns.pop(idx)
            self._compiled.pop(idx)
            self._save()

    # ------------------------------------------------------------------
    # マッチング
    # ------------------------------------------------------------------

    def matches(self, line: str) -> bool:
        """行テキストがいずれかのパターンにマッチするか判定する。"""
        for compiled in self._compiled:
            if compiled.search(line):
                return True
        return False

    # ------------------------------------------------------------------
    # プロパティ
    # ------------------------------------------------------------------

    @property
    def settings_path(self) -> Path:
        """設定ファイルの絶対パスを返す。"""
        return _SETTINGS_FILE
