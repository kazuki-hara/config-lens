"""フォルダ比較ロジックモジュール。

2 つのフォルダを走査し、ファイル単位の差分状態を返す。
GUI に依存しないピュアなビジネスロジックを提供する。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class FileDiffEntry:
    """フォルダ比較の 1 ファイル分の結果。

    Attributes:
        filename: ファイル名（相対パス）
        status: 差分状態
        left_path: 左フォルダ側のフルパス（存在しない場合は None）
        right_path: 右フォルダ側のフルパス（存在しない場合は None）
    """

    filename: str
    status: Literal["same", "diff", "only_left", "only_right"]
    left_path: Path | None
    right_path: Path | None


class FolderDiffScanner:
    """2 つのフォルダを走査してファイル単位の差分を検出するスキャナー。

    walk_depth=1 でフラットスキャン、walk_depth=-1 で再帰スキャン。
    差分判定はバイナリ比較ではなくテキストの内容一致比較を使用する。
    """

    def __init__(self, walk_depth: int = 1) -> None:
        """初期化。

        Args:
            walk_depth: スキャン深さ（1=フラット、-1=再帰）
        """
        self._walk_depth = walk_depth

    def scan(
        self, left_dir: Path, right_dir: Path
    ) -> list[FileDiffEntry]:
        """2 つのフォルダを走査してファイル差分リストを返す。

        Args:
            left_dir: 左フォルダのパス
            right_dir: 右フォルダのパス

        Returns:
            FileDiffEntry のリスト。ファイル名昇順でソート済み。

        Raises:
            ValueError: left_dir または right_dir がディレクトリでない場合
        """
        if not left_dir.is_dir():
            raise ValueError(
                f"左フォルダが存在しません: {left_dir}"
            )
        if not right_dir.is_dir():
            raise ValueError(
                f"右フォルダが存在しません: {right_dir}"
            )

        left_files = self._collect_files(left_dir)
        right_files = self._collect_files(right_dir)

        all_names = sorted(left_files.keys() | right_files.keys())
        entries: list[FileDiffEntry] = []

        for name in all_names:
            lp = left_files.get(name)
            rp = right_files.get(name)

            if lp is not None and rp is None:
                status: Literal["same", "diff", "only_left", "only_right"] = (
                    "only_left"
                )
            elif lp is None and rp is not None:
                status = "only_right"
            elif lp is not None and rp is not None:
                status = "same" if self._is_same(lp, rp) else "diff"
            else:
                continue  # 到達しないが型安全のため

            entries.append(
                FileDiffEntry(
                    filename=name,
                    status=status,
                    left_path=lp,
                    right_path=rp,
                )
            )

        return entries

    def _collect_files(self, root: Path) -> dict[str, Path]:
        """フォルダ内のファイルを収集して {相対パス: フルパス} の辞書を返す。

        Args:
            root: 走査するルートフォルダ

        Returns:
            相対パス文字列をキーとしたファイルパス辞書
        """
        result: dict[str, Path] = {}
        if self._walk_depth == 1:
            for p in root.iterdir():
                if p.is_file():
                    result[p.name] = p
        else:
            for p in root.rglob("*"):
                if p.is_file():
                    rel = str(p.relative_to(root))
                    result[rel] = p
        return result

    @staticmethod
    def _is_same(left: Path, right: Path) -> bool:
        """2 つのファイルの内容が同一かどうかを判定する。

        テキストファイルを UTF-8 で読み込み、内容を比較する。
        デコードできない場合はバイナリ比較にフォールバックする。

        Args:
            left: 左ファイルのパス
            right: 右ファイルのパス

        Returns:
            内容が同一であれば True
        """
        try:
            return left.read_text("utf-8") == right.read_text("utf-8")
        except (UnicodeDecodeError, OSError):
            return left.read_bytes() == right.read_bytes()
