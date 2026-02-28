# Changelog

このファイルはバージョンごとの変更内容を記録します。
形式は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。

---

## [0.4.0] - 2026-02-28

### 追加
- **L2SW VLAN トランク正規化機能**（`src/compare/normalizer.py`）— `switchport trunk allowed vlan add` で VLAN ID が複数行に跨るコンフィグを、VLAN ID をレンジ表記にまとめた単一行に正規化してから差分比較を行う
- **VLAN 差分アノテーション行**（`normalize_vlan_trunk_pair`）— 同インターフェースの VLAN 構成に差分がある場合、VLANトランク行の直後に `! [vlan diff]  -delete:96  +add:161,169` 形式の情報行を両側に挿入。差分比較エンジンが `equal` と認識するため左右同行にグレーで表示される
- `expand_vlan_ids()` — カンマ区切り・ハイフン範囲指定の VLAN ID 文字列を整数セットに展開
- `vlan_ids_to_ranges()` — 整数セットを連続 ID をレンジ化したコンパクト文字列に変換（例: `{1,2,3,10}` → `"1-3,10"`）
- `compare_and_align`・`compare_and_align_with_diff_info`・`compare_and_align_with_structural_diff_info` に `normalize: bool = False` パラメータを追加

### 変更
- GUI（`result_window.py`）と CLI（`cli.py`）のファイル比較で常時 `normalize=True` を設定し、L2SW コンフィグの VLAN 差分を自動的に正確検知するように変更
- アノテーション行（`! [vlan diff]`）は `vlan_annotation` タグでグレー着色、ナビゲーション対象外

### 内部改善
- `normalize_vlan_trunk_config` をインターフェースブロック単位で処理するように再設計。`switchport mode trunk` が init 行と add 行の間に挟まれた実機コンフィグでも正しく動作
- テスト追加：`tests/compare/test_normalizer.py`（36 件、全 161 件通過）
- テストフィクスチャ更新：`tests/fixtures/vlan/l2sw_source.txt`・`l2sw_target.txt` をレンジ表記の実機相当コンフィグに更新

---

## [0.3.0] - 2026-02-28

### 追加
- **WinMerge ライクな統合 UI（OpenView）** — サイドバーを廃止し、左右 2 列の大型ドロップゾーンを持つ単一エントリポイントに刷新
- **ドラッグ & ドロップ対応**（tkinterdnd2） — ファイル・フォルダをドロップゾーンへ直接ドラッグして読み込み可能。ドラッグ中は対象ゾーンが青くハイライト
- **フォルダ比較機能** — 左右フォルダを指定すると、配下ファイルの追加・削除・変更・一致をスキャンしてリスト表示
- **フリーペア比較** — フォルダ比較画面で「← 左に」「右に →」ボタンにより任意のファイルをペア選択し、ファイル単位の差分比較を実行
- **パスバー**（`_PathBar`）— 常時表示。`grid + uniform` で左右を厳密に 50/50 分割し、選択済みパスを表示
- **CLI インターフェイス**（`src/cli.py`）— コマンドライン引数でファイルをあらかじめ指定して起動可能

### 変更
- **ナビゲーションバー（サイドバー）を廃止** — `src/menu.py`・`src/diff.py`・`src/compare/view.py` を削除し、`OpenView` に一本化
- **比較結果ウィンドウを独立させる**（`src/compare/result_window.py`）— 同一ファイルペアは重複ウィンドウを開かない
- **起動時の前回パス復元を廃止** — 毎回クリーンな状態で起動

### 内部改善
- `src/compare/folder_logic.py` 新設 — フォルダスキャン・`FileDiffEntry` を専用モジュールへ分離
- `_PathBar` クラス分離 — パスバーの再利用性・テスタビリティを向上
- テスト追加：`tests/compare/test_folder_logic.py`・`tests/test_cli.py`（全 125 件通過）

---

## [0.2.2] - 2026-02-25

### 追加
- **Compare 機能に Next/Prev ナビゲーションを追加** — ツールバー下のナビバーで差分行（削除・追加・順番違い）を順送り/逆戻りでジャンプ。左右テキストの同期スクロール仕様を維持
- **現在ナビ位置の行を白反転強調表示** — `nav_current` タグで現在位置をひと目で確認できるよう強調

### 修正
- **Compare テキストボックスを読み取り専用に変更** — 比較結果エリアへの誤入力を防止（ジャンプ機能は引き続き動作）

### パフォーマンス
- **マウスホイールスクロール速度を高速化** — 1ノッチあたり 1行 → 3行 に変更（`_SCROLL_SPEED` 定数で調整可能）

---

## [0.2.1] - 2026-02-25

### 追加
- **Validate 機能に reorder 行のジャンプ機能を追加** — 変更内容の黄色行をクリックすると、running-config／expected-config の対応 reorder 行へスクロール＆ハイライト

### 修正
- **Compare 機能のテキストボックスを読み取り専用に変更** — 比較結果エリアへの誤入力を防止（ジャンプ機能は引き続き動作）

### ドキュメント
- **macOS 向けリリースノートのインストール手順を更新** — 「右クリックで開く」から「システム設定 → プライバシーとセキュリティ」での許可方法および `xattr` コマンドの案内へ変更

---

## [0.2.0] - 2026-02-24

### 追加
- **Config Validator 機能** — 現在の running-config・設定変更内容・想定される running-configの 3 ファイルを入力し、差分が設定変更内容で説明できるかを検証する機能を追加
  - `change_remove`（黄）/ `remove`（赤、検証エラー）/ `change_add`（黄）/ `add`（緑、検証エラー）の 4層ハイライト
  - 設定変更内容の黄色行をクリックすると対応差分行をハイライト（連動機能）
  - 説明できない差分が調査導きの欠れは `unmatched`（グレー）として表示
- **ナビゲーションバーに 「Config Validator」 ボタンを追加**
- **ナビゲーションバーにアプリバージョンを表示**
- **左右テキストエリアの同期スクロール** — マウスホイール・スクロールバードラッグで左右が連動する（Windows / macOS / Linux 対応）

### 修正
- **replace ブロック内の行整列バグを修正** — 異なる設定行が誤って横に並んでいた問題を解決。replace ブロック内で改めて階層キーを再マッチングし、一致する行のみ横に並べるよう改善
- **macOS 配布時のフォルダ名不具合を修正**
- **macOS ビルド時のアドホック署名を適用**（ダウンロード後に起動できない問題を解決）

### 内部改善（影響なし）
- `PLATFORM_MAP` を `src/compare/platforms.py` に一元管理（`compare/view.py`・`validate/view.py` の重複定義を解消）
- `calcurate_hierarcihical_path` → `calculate_hierarchical_path` にリネーム（スペルミス修正）
- `validate/logic.py` の未使用定数 `LINE_NUM_WIDTH` を削除
- テストアーキテクチャ（`tests/validate/` 新設）とフィクスチャファイル（`eBGP/`・`vlan/`）を整備
- `docs/architecture.md`・`docs/development.md` を機能追加に合わせて更新
- `README.md`・`docs/user-guide.md` のmacOSインストール手順を「`システム設定`→`プライバシーとセキュリティ`で許可」に文言統一

---

## [0.1.0] - 2026-02-23

### 追加
- ネットワーク機器のコンフィグファイルを2列で差分比較する機能
- 差分の色分け表示（追加: 緑、削除: 赤、変更なし: グレー）
- 階層構造を考慮した比較（Cisco IOS 対応）
- 無視パターン（正規表現）の登録・管理機能
- macOS / Windows 向けスタンドアロンアプリのビルド対応
