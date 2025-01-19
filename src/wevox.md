# WEVOX システム更新マニュアル

## 目次

1. [はじめに](#はじめに)
2. [WEVOX 更新の概要](#wevox-更新の概要)
   - [WEVOX とは](#wevox-とは)
   - [ユーザーの種類](#ユーザーの種類)
3. [月初の作業手順](#月初の作業手順)
   - [概要](#概要)
   - [使用するファイル](#使用するファイル)
   - [作業手順](#作業手順)
4. [データ処理の詳細](#データ処理の詳細)
   - [ステップ 1: 組織ツリーの作成](#ステップ-1-組織ツリーの作成)
   - [ステップ 2: Admin ユーザーのインポートデータ作成](#ステップ-2-admin-ユーザーのインポートデータ作成)
   - [ステップ 3: エンゲージメントユーザーのインポートデータ作成](#ステップ-3-エンゲージメントユーザーのインポートデータ作成)
5. [重要な考慮点](#重要な考慮点)
   - [組織変更の扱い](#組織変更の扱い)
   - [雇用形態区分の判定](#雇用形態区分の判定)
   - [個別条件の適用](#個別条件の適用)
6. [ファイル仕様](#ファイル仕様)
   - [システムエクスポートファイル](#システムエクスポートファイル)
   - [申請書ファイル](#申請書ファイル)
   - [WEVOX エクスポートファイル](#wevox-エクスポートファイル)
   - [作成するインポートファイル](#作成するインポートファイル)
7. [Python ツールへの移行](#python-ツールへの移行)

---

## はじめに

本マニュアルは、WEVOX システムの更新作業を効率的かつ正確に行うための手順をまとめたものです。特に月初に実施する作業について詳細に記載しています。

## WEVOX 更新の概要

### WEVOX とは

WEVOX は、簡単に回答できるサーベイで従業員のエンゲージメントを測定・集計するサービスです。エンゲージメントはグループ単位でまとめられ、ユーザー個人には紐づきません。

### ユーザーの種類

- **Admin ユーザー**: 全社員分のデータを登録します。メール送信が行われるため、社外のメールを受信できる人のみが対象です。
- **Engagement ユーザー**: エンゲージメント集計の対象となるユーザーです。Deliver フラグがあり、設問を送信するか否かを制御します。社長や休職者など、配信対象外とするユーザーも含まれますが、Deliver フラグを調整します。

## 月初の作業手順

### 概要

- **作業頻度**: 月に 2 回（主に月初と月末）
- **主な作業内容**:
  - メンバーの更新
  - グループの更新
  - 閲覧権限の設定

### 使用するファイル

- **システムエクスポートファイル**:
  - `user.csv`
  - `org.csv`
  - `user_org_title.csv`
  - `title.csv`
  - `location.csv`
- **申請書ファイル**:
  - `配信申請書.xlsx`
    - 条件シート
    - 個別条件シート（複数枚）
- **WEVOX エクスポートファイル（前月分）**:
  - `deliver_flg.xlsx`
  - `メンバー.xlsx`
  - `グループ.xlsx`

### 作業手順

1. **申請書の受領と確認**: 月初 5 営業日以内に送付される申請書を受領し、不備がないか確認します。
2. **インポートデータの作成**: 申請書に基づき、ユーザーおよびグループのインポートデータを作成します。
3. **データのインポート**: 作成したデータを WEVOX にインポートします。
4. **閲覧権限の設定**: 必要に応じて閲覧権限を設定します。

## データ処理の詳細

### ステップ 1: 組織ツリーの作成

- **目的**: 組織コードをもとに、`/` 区切りの組織ツリーを作成し、他の処理で利用します。
- **手順**:
  - `org.csv` を使用し、親子関係を辿って組織ツリーを生成します。
  - 組織ランクが飛ぶ場合は「その他」を挿入します。
- **生成されるテーブル**: `org_tree`
  - カラム: `組織コード`, `組織ツリー`

### ステップ 2: Admin ユーザーのインポートデータ作成

- **目的**: WEVOX に全社員の情報をインポートします。
- **手順**:
  - `user.csv`, `user_org_title.csv`, `org_tree` を結合し、`export_admin` テーブルを作成します。
  - グループ情報 (`group` カラム) には以下を含めます:
    - 拠点（全員）
    - 入社年度（派遣社員以外）
    - 組織ツリー
  - **条件の適用**:
    - `配信申請書.xlsx` の条件シートの「配下含む」と「雇用形態組織作成」を考慮します。
    - 「雇用形態組織作成」が `true` の場合、組織ツリーの末尾に雇用形態（正社員、派遣社員、契約社員）を追加します。
  - **雇用形態区分の設定**:
    - 社員番号の先頭文字で判定します。
      - `H` または `G` 始まり: 派遣社員
      - `Q` 始まり: 契約社員
      - その他: 正社員

### ステップ 3: エンゲージメントユーザーのインポートデータ作成

- **目的**: エンゲージメントを取得するユーザーを特定し、Deliver フラグを設定します。
- **手順**:
  1. **初期抽出**:
     - `export_admin` テーブルから、`配信申請書.xlsx` の条件シートに一致するユーザーを抽出します。
     - 「配下含む」が `true` の場合は配下組織も含めます。
     - 雇用形態（正社員、派遣社員、契約社員）の条件を適用します。
  2. **個別条件の適用**:
     - 個別条件シートに基づき、ユーザーごとに以下のアクションを適用します:
       - `追加`: 既存の組織に加えて、新たな組織を追加。
       - `置き換え`: 既存の組織を新たな組織に置き換え。
       - `削除`: エンゲージメントの配信対象から除外。ただし、Admin ユーザーとしては残す。
  3. **Deliver フラグの設定**:
     - `deliver_flg.xlsx` を更新し、配信対象ユーザーの `deliver_flg` を `true`、非対象ユーザーを `false` に設定します。

## 重要な考慮点

### 組織変更の扱い

- 組織名が変更された場合、エンゲージメントデータがリセットされる可能性があります。
- 組織の大幅な変更があった場合は、以下の対応が必要です:
  - 既存の組織名を別名に変更。
  - 新しい組織をインポートし、エンゲージメントを新規に取得。

### 雇用形態区分の判定

- 社員番号で雇用形態を判定します。
  - `H` または `G` 始まり: 派遣社員
  - `Q` 始まり: 契約社員
  - その他: 正社員

### 個別条件の適用

- 個別条件シートで指定されたユーザーに対しては、特別な処理を行います。
  - **追加**: ユーザーに新たな組織を追加。
  - **置き換え**: ユーザーの所属組織を指定の組織に置き換え。
  - **削除**: エンゲージメントの配信対象から除外。

## ファイル仕様

### システムエクスポートファイル

- **`user.csv`**
  - カラム: `社員番号`, `氏名`, `拠点`, `資格コード`, `職位コード`, `入社年度`, `メールアドレス`
- **`user_org_title.csv`**
  - カラム: `社員番号`, `組織コード`, `役職コード`, `兼務フラグ`
- **`org.csv`**
  - カラム: `組織コード`, `上位組織コード`, `組織名`, `組織ランク`
- **`title.csv`**
  - カラム: `役職コード`, `役職名`

### 申請書ファイル

- **`配信申請書.xlsx`**
  - **条件シート**:
    - カラム: `組織コード`, `配下含む (true|false)`, `正社員 (true|false)`, `派遣社員 (true|false)`, `契約社員 (true|false)`, `雇用形態組織作成 (true|false)`
  - **個別条件シート（複数枚）**:
    - カラム: `社員番号`, `組織名`, `アクション区分 (追加|置き換え|削除)`

### WEVOX エクスポートファイル

- **`deliver_flg.xlsx`**
  - カラム: `メールアドレス`, `deliver_flg`
- **`メンバー.xlsx`**
  - カラム: `社員番号`, `氏名`, `メールアドレス`, `group`, `label`, `雇用形態区分`
- **`グループ.xlsx`**
  - カラム: `group_id`, `group_fullname`

### 作成するインポートファイル

- **`admin_members.xlsx`**
  - カラム: `社員番号`, `氏名`, `メールアドレス`, `group`, `label`, `雇用形態区分`
- **`group_01.xlsx`（リネーム用）**
  - カラム: `group_id`, `group_fullname`
- **`group_02.xlsx`（追加・更新用）**
  - カラム: `group_id`, `group_fullname`
- **`deliver_flag.xlsx`**
  - カラム: `メールアドレス`, `deliver_flg`

## Python ツールへの移行

現在、MS-Access で作成されたツールを Python に移行する計画があります。以下の点を考慮して進めてください。

- **使用ライブラリ**: `pandas`, `openpyxl`
- **目的**:
  - コードの簡素化と可読性の向上
  - データ処理の効率化
- **ポイント**:
  - 既存の処理手順を Python スクリプトに置き換える
  - 各ステップで何を行っているかをコメントやドキュメントで明確にする

---

以上が、WEVOX システム更新作業のマニュアルとなります。不明点や追加の質問があれば、お知らせください。

## 必要な関数名リスト

以下は、WEVOX システム更新作業を Python で実装する際に必要となるであろう関数名の一覧です。各関数名には簡単な説明も付け加えています。

```markdown
# WEVOX 更新用 Python 関数リスト

## データ読み込み関数

- `load_csv(file_path: str) -> pd.DataFrame`

  - 指定されたパスから CSV ファイルを読み込み、DataFrame として返します。

- `load_excel(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame`
  - 指定されたパスから Excel ファイルを読み込み、必要に応じてシートを指定して DataFrame として返します。

## データ検証関数

- `validate_user_data(user_df: pd.DataFrame) -> bool`

  - ユーザーデータの整合性や必要なフィールドの存在を検証します。

- `validate_org_data(org_df: pd.DataFrame) -> bool`

  - 組織データの整合性や階層構造を検証します。

- `validate_conditions(conditions_df: pd.DataFrame) -> bool`
  - 配信申請書の条件シートの内容を検証します。

## データ変換・処理関数

- `create_org_tree(org_df: pd.DataFrame) -> pd.DataFrame`

  - 組織データから`/`区切りの組織ツリーを生成します。

- `determine_employment_type(employee_number: str) -> str`

  - 社員番号の先頭文字に基づいて雇用形態（正社員、契約社員、派遣社員）を判定します。

- `extract_admin_users(user_df: pd.DataFrame, user_org_title_df: pd.DataFrame, org_tree_df: pd.DataFrame) -> pd.DataFrame`

  - Admin ユーザーのデータを抽出します。

- `extract_engagement_users(admin_df: pd.DataFrame, deliver_flg_df: pd.DataFrame) -> pd.DataFrame`

  - エンゲージメント対象ユーザーを抽出し、Deliver フラグを設定します。

- `apply_conditions(admin_df: pd.DataFrame, conditions_df: pd.DataFrame) -> pd.DataFrame`

  - 配信申請書の条件シートに基づいてユーザーをフィルタリングします。

- `apply_individual_conditions(admin_df: pd.DataFrame, individual_conditions_df: pd.DataFrame) -> pd.DataFrame`
  - 個別条件シートに基づいてユーザーの組織所属を調整します。

## データ出力・エクスポート関数

- `export_to_excel(df: pd.DataFrame, file_path: str) -> None`

  - DataFrame を指定されたパスに Excel ファイルとしてエクスポートします。

- `create_import_files(admin_df: pd.DataFrame, group_df: pd.DataFrame, deliver_flag_df: pd.DataFrame) -> None`
  - 必要なインポートファイル（`admin_members.xlsx`、`group_01.xlsx`、`group_02.xlsx`、`deliver_flag.xlsx`）を作成します。

## グループ管理関数

- `rename_group(group_df: pd.DataFrame, rename_mapping: Dict[str, str]) -> pd.DataFrame`

  - グループ名を指定されたマッピングに基づいてリネームします。

- `update_group(group_df: pd.DataFrame, update_data: pd.DataFrame) -> pd.DataFrame`
  - グループデータを追加・更新します。

## ユーティリティ関数

- `remove_excluded_users(admin_df: pd.DataFrame, excluded_users_df: pd.DataFrame) -> pd.DataFrame`

  - 退職者や休職者を Admin ユーザーから除外します。

- `check_org_consistency(current_org_df: pd.DataFrame, previous_org_df: pd.DataFrame) -> bool`

  - 現在の組織データと前月の組織データを比較し、一貫性を確認します。

- `handle_org_changes(org_df: pd.DataFrame, org_tree_df: pd.DataFrame) -> None`
  - 組織の変更を正しく処理し、エンゲージメントデータがリセットされないようにします。

## インポート処理関数

- `import_data_to_wevox(import_file_path: str) -> None`

  - 作成したインポートファイルを WEVOX システムにインポートします。

- `update_permission_settings(permission_df: pd.DataFrame) -> None`
  - 閲覧権限の設定を更新します。
```

---

## 説明書のダウンロード方法

現在、直接ダウンロードリンクを提供することはできませんが、以下の手順でマニュアルをローカルに保存することができます。

1. **マニュアル内容をコピー**:

   - 画面上のマニュアルテキストを全て選択し、コピーします。

2. **テキストエディタを開く**:

   - お使いのコンピュータで任意のテキストエディタ（例: VS Code, Sublime Text, Notepad++ など）を開きます。

3. **新しいファイルを作成**:

   - 新規ファイルを作成し、コピーしたマニュアル内容を貼り付けます。

4. **ファイルを保存**:

   - ファイル名を `WEVOX_Update_Manual.md` として保存します。拡張子を `.md` とすることで Markdown 形式のファイルとして保存されます。

5. **Markdown ビューアで確認**:
   - 保存したファイルを Markdown 対応のビューアやエディタで開くと、フォーマットが適用された状態で内容を確認できます。

---

もし他に必要な情報や追加のサポートが必要であれば、お知らせください。



```mermaid
sequenceDiagram
    actor HR as 人事部門<br>(WLS)
    participant Admin as データ管理者<br>(社内SS)
    participant IT as システム部門<br>(GOD)
    participant WEVOX as WEVOXシステム

    Note over HR,WEVOX: 月初5営業日以内に開始
    
    %% 申請データ提供フェーズ
    HR->>+Admin: 申請書の提供<br>(配信申請・閲覧権限申請)
    HR->>Admin: 休職・産休育休リストの提供
    
    %% データ確認フェーズ
    activate Admin
    Admin->>Admin: データチェック<br>1. フォーマット確認<br>2. 必須項目確認<br>3. 組織コード確認
    
    alt データに問題がある場合
        Admin-->>HR: 修正依頼
        HR->>Admin: 修正データ提供
    end
    deactivate Admin

    %% システム更新フェーズ
    Note over Admin,IT: 15-16日頃までに完了
    Admin->>+IT: GODデータ更新要求
    IT->>+WEVOX: データインポート処理
    
    alt インポートエラー発生
        WEVOX-->>IT: エラー通知
        IT->>IT: エラー原因調査
        IT->>WEVOX: 再インポート
    end
    
    WEVOX-->>-IT: インポート完了通知
    IT-->>-Admin: 更新完了報告

    %% 直接データ処理フェーズ
    opt WEVOXシステムからの要求がある場合
        WEVOX->>+Admin: データ要求
        Admin->>Admin: データ作成・確認
        Admin->>WEVOX: データ提供
        WEVOX-->>-Admin: 受領確認
    end

    Note over HR,WEVOX: 月末までに完了

    %% 完了確認フェーズ
    Admin->>Admin: 最終確認<br>1. 組織更新確認<br>2. 配信設定確認
```