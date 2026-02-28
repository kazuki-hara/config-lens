"""FolderDiffScanner および FileDiffEntry のテスト。"""

import pytest

from src.compare.folder_logic import FileDiffEntry, FolderDiffScanner


class TestFileDiffEntry:
    """FileDiffEntry データクラスのテスト。"""

    def test_frozen_instance_cannot_be_mutated(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """frozen=True のため属性変更が禁止されていることを確認する。"""
        entry = FileDiffEntry(
            filename="a.txt",
            status="same",
            left_path=None,
            right_path=None,
        )
        with pytest.raises(Exception):
            entry.filename = "b.txt"  # type: ignore[misc]

    def test_status_values_are_literals(self) -> None:
        """status に期待する 4 値が設定できることを確認する。"""
        for status in ("same", "diff", "only_left", "only_right"):
            entry = FileDiffEntry(
                filename="f.txt",
                status=status,  # type: ignore[arg-type]
                left_path=None,
                right_path=None,
            )
            assert entry.status == status


class TestFolderDiffScannerValidation:
    """FolderDiffScanner の入力バリデーションのテスト。"""

    def test_raises_when_left_dir_does_not_exist(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """存在しない左フォルダを指定すると ValueError が発生する。"""
        scanner = FolderDiffScanner()
        fake = tmp_path / "no_such_dir"  # type: ignore[operator]
        with pytest.raises(ValueError, match="左フォルダが存在しません"):
            scanner.scan(fake, tmp_path)  # type: ignore[arg-type]

    def test_raises_when_right_dir_does_not_exist(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """存在しない右フォルダを指定すると ValueError が発生する。"""
        scanner = FolderDiffScanner()
        fake = tmp_path / "no_such_dir"  # type: ignore[operator]
        with pytest.raises(ValueError, match="右フォルダが存在しません"):
            scanner.scan(tmp_path, fake)  # type: ignore[arg-type]


class TestFolderDiffScannerFlatScan:
    """walk_depth=1（フラットスキャン）時の差分検出テスト。"""

    @pytest.fixture()
    def dirs(self, tmp_path: pytest.TempPathFactory):
        """左右フォルダのベースを返すフィクスチャ。"""
        left = tmp_path / "left"  # type: ignore[operator]
        right = tmp_path / "right"  # type: ignore[operator]
        left.mkdir()
        right.mkdir()
        return left, right

    def test_same_files_are_detected(self, dirs) -> None:
        """両フォルダに同一内容のファイルが存在するとき status が 'same' になる。"""
        left, right = dirs
        (left / "a.txt").write_text("hello", encoding="utf-8")
        (right / "a.txt").write_text("hello", encoding="utf-8")

        entries = FolderDiffScanner().scan(left, right)

        assert len(entries) == 1
        assert entries[0].filename == "a.txt"
        assert entries[0].status == "same"
        assert entries[0].left_path == left / "a.txt"
        assert entries[0].right_path == right / "a.txt"

    def test_diff_files_are_detected(self, dirs) -> None:
        """両フォルダに異なる内容のファイルが存在するとき status が 'diff' になる。"""
        left, right = dirs
        (left / "router.cfg").write_text("ip address 1.1.1.1", encoding="utf-8")
        (right / "router.cfg").write_text("ip address 2.2.2.2", encoding="utf-8")

        entries = FolderDiffScanner().scan(left, right)

        assert len(entries) == 1
        assert entries[0].status == "diff"

    def test_only_left_file_is_detected(self, dirs) -> None:
        """左フォルダにのみ存在するファイルは status が 'only_left' になる。"""
        left, right = dirs
        (left / "left_only.txt").write_text("left", encoding="utf-8")

        entries = FolderDiffScanner().scan(left, right)

        assert len(entries) == 1
        assert entries[0].status == "only_left"
        assert entries[0].left_path is not None
        assert entries[0].right_path is None

    def test_only_right_file_is_detected(self, dirs) -> None:
        """右フォルダにのみ存在するファイルは status が 'only_right' になる。"""
        left, right = dirs
        (right / "right_only.txt").write_text("right", encoding="utf-8")

        entries = FolderDiffScanner().scan(left, right)

        assert len(entries) == 1
        assert entries[0].status == "only_right"
        assert entries[0].left_path is None
        assert entries[0].right_path is not None

    def test_entries_are_sorted_by_filename(self, dirs) -> None:
        """結果がファイル名昇順でソートされていることを確認する。"""
        left, right = dirs
        for name in ("c.txt", "a.txt", "b.txt"):
            (left / name).write_text(name, encoding="utf-8")
            (right / name).write_text(name, encoding="utf-8")

        entries = FolderDiffScanner().scan(left, right)

        assert [e.filename for e in entries] == ["a.txt", "b.txt", "c.txt"]

    def test_empty_folders_return_empty_list(self, dirs) -> None:
        """両フォルダが空のとき空リストを返す。"""
        left, right = dirs
        entries = FolderDiffScanner().scan(left, right)
        assert entries == []

    def test_mixed_statuses(self, dirs) -> None:
        """same / diff / only_left / only_right が混在するケース。"""
        left, right = dirs
        (left / "same.txt").write_text("x", encoding="utf-8")
        (right / "same.txt").write_text("x", encoding="utf-8")
        (left / "diff.txt").write_text("old", encoding="utf-8")
        (right / "diff.txt").write_text("new", encoding="utf-8")
        (left / "left.txt").write_text("l", encoding="utf-8")
        (right / "right.txt").write_text("r", encoding="utf-8")

        entries = FolderDiffScanner().scan(left, right)

        status_map = {e.filename: e.status for e in entries}
        assert status_map["same.txt"] == "same"
        assert status_map["diff.txt"] == "diff"
        assert status_map["left.txt"] == "only_left"
        assert status_map["right.txt"] == "only_right"

    def test_flat_scan_ignores_subdirectories(self, dirs) -> None:
        """walk_depth=1 のとき、サブディレクトリ内のファイルは無視される。"""
        left, right = dirs
        sub = left / "subdir"
        sub.mkdir()
        (sub / "nested.txt").write_text("nested")

        entries = FolderDiffScanner(walk_depth=1).scan(left, right)

        filenames = [e.filename for e in entries]
        assert "nested.txt" not in filenames
        assert not any("subdir" in f for f in filenames)


class TestFolderDiffScannerRecursiveScan:
    """walk_depth=-1（再帰スキャン）時のテスト。"""

    def test_recursive_scan_detects_nested_files(self, tmp_path) -> None:
        """再帰スキャンでサブディレクトリ内のファイルが検出される。"""
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        sub_l = left / "sub"
        sub_r = right / "sub"
        sub_l.mkdir()
        sub_r.mkdir()
        (sub_l / "nested.cfg").write_text("same", encoding="utf-8")
        (sub_r / "nested.cfg").write_text("same", encoding="utf-8")

        entries = FolderDiffScanner(walk_depth=-1).scan(left, right)

        filenames = [e.filename for e in entries]
        assert any("nested.cfg" in f for f in filenames)

    def test_recursive_scan_detects_nested_diff(self, tmp_path) -> None:
        """再帰スキャン時にサブディレクトリ内の差分が検出される。"""
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        sub_l = left / "sub"
        sub_r = right / "sub"
        sub_l.mkdir()
        sub_r.mkdir()
        (sub_l / "cfg.txt").write_text("old", encoding="utf-8")
        (sub_r / "cfg.txt").write_text("new", encoding="utf-8")

        entries = FolderDiffScanner(walk_depth=-1).scan(left, right)

        diff_entries = [e for e in entries if e.status == "diff"]
        assert len(diff_entries) == 1
