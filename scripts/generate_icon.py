"""assets/icon.png から icon.icns / icon.ico を生成するスクリプト。

依存: Pillow
macOS の .icns 生成には OS 標準の iconutil コマンドを使用する。
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

# macOS 向け iconset のサイズ定義 (size, scale)
_ICONSET_SPECS: list[tuple[int, int]] = [
    (16, 1), (16, 2),
    (32, 1), (32, 2),
    (128, 1), (128, 2),
    (256, 1), (256, 2),
    (512, 1), (512, 2),
]

# Windows .ico に埋め込むサイズ
_ICO_SIZES: list[tuple[int, int]] = [(16, 16), (32, 32), (48, 48), (256, 256)]


def generate_icns(src: Path, output_path: Path) -> None:
    """icon.png から macOS 用 .icns を生成する。

    iconutil（macOS 標準）を使用するため、macOS 環境でのみ動作する。

    Args:
        src: 元の PNG ファイルパス。
        output_path: 出力する .icns のパス。

    Raises:
        RuntimeError: iconutil が見つからない場合。
    """
    if not shutil.which("iconutil"):
        raise RuntimeError("iconutil が見つかりません。macOS 環境で実行してください。")

    img = Image.open(src).convert("RGBA")

    with tempfile.TemporaryDirectory(suffix=".iconset") as tmp:
        iconset = Path(tmp)
        for size, scale in _ICONSET_SPECS:
            px = size * scale
            resized = img.resize((px, px), Image.LANCZOS)
            suffix = f"@{scale}x" if scale > 1 else ""
            filename = f"icon_{size}x{size}{suffix}.png"
            resized.save(iconset / filename, format="PNG")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(output_path)],
            check=True,
        )

    print(f"生成完了: {output_path}")


def generate_ico(src: Path, output_path: Path) -> None:
    """icon.png から Windows 用 .ico を生成する（Pillow 使用）。

    Args:
        src: 元の PNG ファイルパス。
        output_path: 出力する .ico のパス。
    """
    img = Image.open(src).convert("RGBA")
    images = [img.resize(size, Image.LANCZOS) for size in _ICO_SIZES]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        output_path,
        format="ICO",
        append_images=images[1:],
        sizes=_ICO_SIZES,
    )
    print(f"生成完了: {output_path}")


if __name__ == "__main__":
    assets = Path("assets")
    src_png = assets / "icon.png"

    if not src_png.exists():
        print(f"エラー: {src_png} が見つかりません。", file=sys.stderr)
        sys.exit(1)

    generate_ico(src_png, assets / "icon.ico")

    if shutil.which("iconutil"):
        generate_icns(src_png, assets / "icon.icns")
    else:
        print("iconutil が見つからないため .icns の生成をスキップします（Windows 環境）。")
