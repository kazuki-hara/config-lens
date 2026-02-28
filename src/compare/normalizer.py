"""L2SWコンフィグ正規化モジュール。

``switchport trunk allowed vlan`` が複数行にまたがるケースを
1行に集約し、VLAN IDをソートした正規形に変換する。

Cisco IOS / IOS-XE 系のトランクポート設定例::

    interface GigabitEthernet1/0/1
     switchport trunk allowed vlan 10,20,30
     switchport trunk allowed vlan add 40,50
     switchport mode trunk

上記を以下の正規形に変換する::

    interface GigabitEthernet1/0/1
     switchport trunk allowed vlan 10,20,30,40,50
     switchport mode trunk

これにより、VLAN IDの記載順・行分割方法が異なる 2 つのコンフィグを
正確に差分比較できるようになる。

さらに :func:`normalize_vlan_trunk_pair` を使うと、差分があった
インターフェースの VLAN 行直後にアノテーション行が挿入され、
どの VLAN が追加・削除されたかを視覚的に確認できる::

    ! [vlan diff]  -delete:96,162-168,181-189  +add:96,162-168,181-189
"""

import re

# アノテーション行の識別マーカー（result_window の着色判定に使用）
VLAN_DIFF_ANNOTATION_MARKER = "! [vlan diff]"

# "switchport trunk allowed vlan <IDs>" にマッチ（"add" は除外）
_VLAN_INIT_RE = re.compile(
    r"^(\s*)switchport\s+trunk\s+allowed\s+vlan"
    r"(?!\s+add\b)\s+([\d,\-\s]+)\s*$",
    re.IGNORECASE,
)

# "switchport trunk allowed vlan add <IDs>" にマッチ
_VLAN_ADD_RE = re.compile(
    r"^(\s*)switchport\s+trunk\s+allowed\s+vlan\s+add\s+([\d,\-\s]+)\s*$",
    re.IGNORECASE,
)

# "interface ..." 行の検出
_IFACE_RE = re.compile(r"^interface\s+", re.IGNORECASE)


def expand_vlan_ids(vlan_str: str) -> set[int]:
    """VLAN ID文字列を整数セットに展開する。

    カンマ区切りおよびハイフンによる範囲指定に対応する。

    Args:
        vlan_str: VLAN ID文字列（例: ``"10,20,100-105"``）

    Returns:
        VLAN IDの整数セット

    Raises:
        ValueError: VLAN ID文字列の形式が不正な場合

    Example:
        >>> sorted(expand_vlan_ids("10,20,100-102"))
        [10, 20, 100, 101, 102]
    """
    vlan_ids: set[int] = set()
    for part in vlan_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-", 1)
            start = int(bounds[0].strip())
            end = int(bounds[1].strip())
            vlan_ids.update(range(start, end + 1))
        else:
            vlan_ids.add(int(part))
    return vlan_ids


def vlan_ids_to_ranges(vlan_ids: set[int]) -> str:
    """VLAN IDのセットをコンパクトな範囲表記文字列に変換する。

    連続する ID はハイフン表記にまとめ、カンマ区切りで返す。

    Args:
        vlan_ids: VLAN IDの整数セット

    Returns:
        範囲表記の文字列（例: ``"10,20,96,100-105,200"``）。
        空セットの場合は空文字列を返す。

    Example:
        >>> vlan_ids_to_ranges({10, 11, 12, 20, 30, 31})
        '10-12,20,30-31'
    """
    if not vlan_ids:
        return ""
    sorted_ids = sorted(vlan_ids)
    ranges: list[str] = []
    start = prev = sorted_ids[0]
    for vid in sorted_ids[1:]:
        if vid == prev + 1:
            prev = vid
        else:
            ranges.append(
                f"{start}-{prev}" if start != prev else str(start)
            )
            start = prev = vid
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ",".join(ranges)


def _normalize_interface_block(block: list[str]) -> list[str]:
    """インターフェースブロック内のVLANトランク行を正規化する。

    ブロック内でインデントのある init 行・add 行を順不同で収集し、
    マージした1行を最初のVLAN行の位置に挿入して返す。

    Args:
        block: ``interface ...`` 行から次の ``interface`` 行直前までの行リスト

    Returns:
        VLANトランク行をマージした行リスト
    """
    has_any_vlan = any(
        _VLAN_INIT_RE.match(line) or _VLAN_ADD_RE.match(line) for line in block
    )
    if not has_any_vlan:
        return block

    accumulated_vlans: set[int] = set()
    first_vlan_idx: int | None = None
    vlan_indent = " "
    non_vlan_lines: list[tuple[int, str]] = []  # (元インデックス, 行)

    for idx, line in enumerate(block):
        init_m = _VLAN_INIT_RE.match(line)
        add_m = _VLAN_ADD_RE.match(line)
        if init_m:
            if first_vlan_idx is None:
                first_vlan_idx = idx
                vlan_indent = init_m.group(1)
            accumulated_vlans.update(expand_vlan_ids(init_m.group(2)))
        elif add_m:
            if first_vlan_idx is None:
                first_vlan_idx = idx
                vlan_indent = add_m.group(1)
            accumulated_vlans.update(expand_vlan_ids(add_m.group(2)))
        else:
            non_vlan_lines.append((idx, line))

    if not accumulated_vlans or first_vlan_idx is None:
        return block

    merged = (
        f"{vlan_indent}switchport trunk allowed vlan"
        f" {vlan_ids_to_ranges(accumulated_vlans)}"
    )

    # 最初のVLAN行の直後かつ次の非VLAN行の前に挿入する
    result: list[str] = []
    inserted = False
    for orig_idx, line in non_vlan_lines:
        if not inserted and orig_idx > first_vlan_idx:
            result.append(merged)
            inserted = True
        result.append(line)
    if not inserted:
        result.append(merged)

    return result


def normalize_vlan_trunk_config(config_text: str) -> str:
    """コンフィグテキスト内のVLANトランク行を正規化する。

    ``switchport trunk allowed vlan`` および
    ``switchport trunk allowed vlan add`` で複数行に跨るVLAN記載を、
    VLAN IDをソート・レンジ化した単一行に統合する。

    インターフェースブロック単位で処理するため、``switchport mode trunk``
    などの非VLAN行が init 行と add 行の間に挟まれていても正しく動作する。

    正規化はテキスト比較に使用するためのものであり、元のファイルは
    変更されない。VLANトランク行が存在しないコンフィグに対しては
    テキストをそのまま返す。

    Args:
        config_text: 正規化対象のコンフィグテキスト

    Returns:
        VLANトランク行を正規化したコンフィグテキスト

    Example:
        >>> config = (
        ...     "interface Gi1/0/1\\n"
        ...     " switchport trunk allowed vlan 10,20\\n"
        ...     " switchport trunk allowed vlan add 30,40\\n"
        ...     " switchport mode trunk"
        ... )
        >>> print(normalize_vlan_trunk_config(config))
        interface Gi1/0/1
         switchport trunk allowed vlan 10,20,30,40
         switchport mode trunk
    """
    lines = config_text.splitlines()
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if _IFACE_RE.match(stripped):
            # インターフェースブロックを収集（次のinterface行の直前まで）
            block: list[str] = [line]
            j = i + 1
            while j < len(lines) and not _IFACE_RE.match(lines[j].strip()):
                block.append(lines[j])
                j += 1
            result.extend(_normalize_interface_block(block))
            i = j
        else:
            result.append(line)
            i += 1
    return "\n".join(result)


def _extract_vlan_info(
    normalized_text: str,
) -> dict[str, tuple[str, set[int]]]:
    """正規化済みコンフィグからインターフェースごとのVLAN情報を抽出する。

    Args:
        normalized_text: :func:`normalize_vlan_trunk_config` 適用後のテキスト

    Returns:
        ``{インターフェース名(小文字) : (インデント文字列, VLAN IDセット)}``
        のマッピング
    """
    result: dict[str, tuple[str, set[int]]] = {}
    current_iface: str | None = None
    for line in normalized_text.splitlines():
        stripped = line.strip()
        if _IFACE_RE.match(stripped):
            current_iface = stripped.lower()
        elif current_iface:
            m = _VLAN_INIT_RE.match(line)
            if m:
                result[current_iface] = (m.group(1), expand_vlan_ids(m.group(2)))
    return result


def _inject_annotations(
    text: str,
    annotations: dict[str, str],
) -> str:
    """正規化済みテキストのVLANトランク行の直後にアノテーション行を挿入する。

    Args:
        text: 正規化済みコンフィグテキスト
        annotations: ``{インターフェース名(小文字) : アノテーション行}``

    Returns:
        アノテーション行を挿入したコンフィグテキスト
    """
    lines = text.splitlines()
    result: list[str] = []
    current_iface: str | None = None
    for line in lines:
        stripped = line.strip()
        if _IFACE_RE.match(stripped):
            current_iface = stripped.lower()
        result.append(line)
        if current_iface and _VLAN_INIT_RE.match(line):
            ann = annotations.get(current_iface)
            if ann:
                result.append(ann)
    return "\n".join(result)


def normalize_vlan_trunk_pair(
    src_text: str,
    tgt_text: str,
) -> tuple[str, str]:
    """両コンフィグを正規化し、VLAN差分アノテーション行を注入する。

    各インターフェースのVLAN構成を比較し、差分がある場合は
    VLANトランク行の直後に両テキスト共通のアノテーション行を挿入する。
    同一文字列を両側に挿入するため、差分比較エンジンは当該行を
    ``"equal"`` と判定し、左右同行にグレーで表示される。

    アノテーション行の例::

        " ! [vlan diff]  -delete:96,162-168  +add:96,162-168,181-189"

    Args:
        src_text: 比較元コンフィグテキスト
        tgt_text: 比較先コンフィグテキスト

    Returns:
        ``(正規化済みsrcテキスト, 正規化済みtgtテキスト)``。
        VLANに差分がある箇所にはアノテーション行が挿入される。
    """
    src_norm = normalize_vlan_trunk_config(src_text)
    tgt_norm = normalize_vlan_trunk_config(tgt_text)

    src_vlans = _extract_vlan_info(src_norm)
    tgt_vlans = _extract_vlan_info(tgt_norm)

    # インターフェースごとに差分を計算してアノテーション文字列を構築
    annotations: dict[str, str] = {}
    for iface in src_vlans:
        if iface not in tgt_vlans:
            continue
        src_indent, src_set = src_vlans[iface]
        _tgt_indent, tgt_set = tgt_vlans[iface]
        src_only = src_set - tgt_set  # src 側だけに存在 (削除)
        tgt_only = tgt_set - src_set  # tgt 側だけに存在 (追加)
        if not src_only and not tgt_only:
            continue
        parts: list[str] = []
        if src_only:
            parts.append(f"-delete:{vlan_ids_to_ranges(src_only)}")
        if tgt_only:
            parts.append(f"+add:{vlan_ids_to_ranges(tgt_only)}")
        ann = f"{src_indent}{VLAN_DIFF_ANNOTATION_MARKER}  {'  '.join(parts)}"
        annotations[iface] = ann

    if not annotations:
        return src_norm, tgt_norm

    return (
        _inject_annotations(src_norm, annotations),
        _inject_annotations(tgt_norm, annotations),
    )
