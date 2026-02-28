"""Config Lens メインエントリーポイント。

引数なし → GUI モード（カスタム Tkinter ウィンドウ）
引数あり → CLI モード（ターミナル出力）
"""

import sys


def main() -> None:
    """GUI / CLI を引数の有無で切り替える。"""
    if len(sys.argv) > 1:
        from src.cli import cli_main

        cli_main()
    else:
        from src.app import main as gui_main

        gui_main()


if __name__ == "__main__":
    main()
