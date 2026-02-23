"""アプリ全体の設定を一元管理するモジュール。

設定はOS標準のユーザーデータディレクトリに JSON 形式で保存される。
  macOS : ~/Library/Application Support/ConfigLens/settings.json
  Windows: %APPDATA%/ConfigLens/settings.json
  Linux  : ~/.local/share/ConfigLens/settings.json

機能ごとの設定は以下のようにネスト構造で管理する。
新しい機能を追加する場合は、対応するセクションを追加するだけでよい。::

    {
        "compare": {
            "ignore": {
                "patterns": ["^!.*", ...]
            }
        }
    }
"""

import json
from pathlib import Path

from platformdirs import user_data_dir

_SETTINGS_DIR: Path = Path(
    user_data_dir(appname="ConfigLens", appauthor=False)
)
_SETTINGS_FILE: Path = _SETTINGS_DIR / "settings.json"


class AppSettings:
    """アプリ全体の設定をネスト構造の JSON で一元管理するクラス。

    機能ごとの設定はセクションパスでネストして管理する。
    新しい機能を追加する場合は対応するセクションパスを使うだけでよい。
    """

    def __init__(self) -> None:
        self._data: dict[str, object] = {}
        self._load()

    # ------------------------------------------------------------------
    # 永続化
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """設定ファイルから読み込む。"""
        if not _SETTINGS_FILE.exists():
            return
        try:
            loaded = json.loads(
                _SETTINGS_FILE.read_text(encoding="utf-8")
            )
            if isinstance(loaded, dict):
                self._data = loaded
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _save(self) -> None:
        """設定ファイルに書き込む。"""
        _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        _SETTINGS_FILE.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # アクセサ
    # ------------------------------------------------------------------

    def get(self, *keys: str, default: object = None) -> object:
        """ネストしたキーパスで設定値を取得する。

        Args:
            *keys: ネストしたキーのパス
            default: キーが存在しない場合のデフォルト値

        Returns:
            設定値。キーが存在しない場合は ``default``。
        """
        d: object = self._data
        for k in keys:
            if not isinstance(d, dict) or k not in d:
                return default
            d = d[k]
        return d

    def update(self, section_path: list[str], value: object) -> None:
        """指定セクションパスの設定値を更新して保存する。

        中間のキーが存在しない場合は自動的に dict を生成する。

        Args:
            section_path: ネストしたキーのパスリスト。
                例: ``["compare", "ignore", "patterns"]``
            value: 設定する値
        """
        if not section_path:
            return
        d: dict[str, object] = self._data
        for k in section_path[:-1]:
            existing = d.get(k)
            if not isinstance(existing, dict):
                d[k] = {}
            d = d[k]  # type: ignore[assignment]
        d[section_path[-1]] = value
        self._save()

    # ------------------------------------------------------------------
    # プロパティ
    # ------------------------------------------------------------------

    @property
    def settings_path(self) -> Path:
        """設定ファイルの絶対パスを返す。"""
        return _SETTINGS_FILE
