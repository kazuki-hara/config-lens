def calculate_hierarchical_path(config: list[str]) -> list[list[str]]:
    """階層構造を持つコンフィグの階層パスを計算する。

    各行のインデント深さを元に親子関係を再構築し、
    各行がどの親ブロック下に属するかをパスリストで返す。

    Args:
        config: コンフィグの行リスト。インデントで階層を表現する。

    Returns:
        各行に対応する階層パスのリスト。
        パスは祖先から自行までのストリップ済み行テキストのリスト。

    Example:
        >>> lines = ["interface Gi0/0", " no shutdown"]
        >>> calculate_hierarchical_path(lines)
        [['interface Gi0/0'], ['interface Gi0/0', 'no shutdown']]
    """
    hierarchical_paths: list[list[str]] = []
    current_path: list[tuple[int, str]] = []
    for line in config:
        indent = len(line) - len(line.lstrip())
        # インデントが同じか浅くなった場合、スタックから余分な要素を除去する
        while current_path and current_path[-1][0] >= indent:
            current_path.pop()
        # 現在行を (インデント幅, ストリップ済みテキスト) でスタックに積む
        current_path.append((indent, line.strip()))
        # 祖先 → 自行の順で結合したパスを記録する
        hierarchical_paths.append([item[1] for item in current_path])
    return hierarchical_paths

def remove_plus_minus_from_diff_line(diff_line: str) -> str:
    """diff 行から先頭の ``+`` または ``-`` 記号とスペースを削除する。

    unified diff 形式の行（``+ added line`` / ``- removed line``）を
    通常のコンフィグ行に戻すために使用する。

    Args:
        diff_line: unified diff 形式の行文字列。

    Returns:
        先頭の ``+ `` または ``- `` を除去した行。記号がない行はそのまま返す。
    """
    if diff_line.lstrip().startswith('+') or diff_line.lstrip().startswith('-'):
        indent = len(diff_line) - len(diff_line.lstrip())
        return " " * indent + diff_line.lstrip()[2:]
    return diff_line