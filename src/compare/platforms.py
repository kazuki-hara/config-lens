"""プラットフォームマッピングの共通定義モジュール。

GUI のプラットフォーム選択肢（文字列）と hier_config の Platform 列挙型を
マッピングする辞書を一元管理する。

``"(Not Supported)"`` サフィックスは将来実装予定のプラットフォームを示す。
現時点で構造的差分解析（hier_config）が実用レベルで動作するのは
CISCO_IOS のみ。
"""

from hier_config import Platform

# GUI 選択肢名 → Platform 列挙型のマッピング
PLATFORM_MAP: dict[str, Platform] = {
    "CISCO_IOS": Platform.CISCO_IOS,
    "CISCO_NXOS (Not Supported)": Platform.CISCO_NXOS,
    "CISCO_XR (Not Supported)": Platform.CISCO_XR,
    "ARISTA_EOS (Not Supported)": Platform.ARISTA_EOS,
    "JUNIPER_JUNOS (Not Supported)": Platform.JUNIPER_JUNOS,
    "FORTINET_FORTIOS (Not Supported)": Platform.FORTINET_FORTIOS,
    "HP_COMWARE5 (Not Supported)": Platform.HP_COMWARE5,
    "HP_PROCURVE (Not Supported)": Platform.HP_PROCURVE,
    "VYOS (Not Supported)": Platform.VYOS,
    "GENERIC (Not Supported)": Platform.GENERIC,
}
