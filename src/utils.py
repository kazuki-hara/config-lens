def calcurate_hierarcihical_path(config: list[str]):
    """階層構造を持つコンフィグの階層パスを計算する

    Args:
        config (list[str]): コンフィグの行のリスト

    Returns:
        list[list[str]]: 各行の階層パスのリスト
    """
    hierarchical_paths = []
    current_path = []
    for line in config:
        indent = len(line) - len(line.lstrip())
        # 階層が上がった場合、current_pathから余分な部分を削除
        while current_path and current_path[-1][0] >= indent:
            current_path.pop()
        # 現在の行をcurrent_pathに追加
        current_path.append((indent, line.strip()))
        # 階層パスを作成して保存
        hierarchical_paths.append([item[1] for item in current_path])
    return hierarchical_paths

def remove_plus_minus_from_diff_line(diff_line: str):
    """diffの行から先頭の+や-を削除する

    Args:
        diff_line (str): diffの行

    Returns:
        str: 先頭の+や-を削除した行
    """
    if diff_line.lstrip().startswith('+') or diff_line.lstrip().startswith('-'):
        indent = len(diff_line) - len(diff_line.lstrip())
        return " " * indent + diff_line.lstrip()[2:]
    else:
        return diff_line