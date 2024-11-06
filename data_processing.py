import os
from logging import getLogger

import numpy as np
import pandas as pd
from data_loader import (
    load_and_prepare_dataframe,
    load_and_prepare_organization_data,
    load_column_config,
    load_dataframe,
)
from data_model import SheetConfig
from data_validation import validate_changes, validate_location_codes

logger = getLogger(__name__)


def reshape_rank_names(df, column_basename, start_rank=3, end_rank=10):
    """
    指定された範囲のランク名列を縦持ちに変換し、重複を排除する関数。

    Parameters:
    df (pd.DataFrame): 元のデータフレーム。
    column_basename (str): 対象となるフィールドのベースネーム（末尾の数字は除いたやつ）
    start_rank (int): 縦持ちに開始するランク（デフォルトは3）。
    end_rank (int): 縦持ちに終了するランク（デフォルトは6）。

    Returns:
    pd.DataFrame: ランク番号と組織名の2列からなる縦持ちのデータフレーム。
    """
    # 対象となるランクのname列をリストアップ
    rank_name_cols = [f"{column_basename}_{i}" for i in range(start_rank, end_rank + 1)]

    # pandasのmelt関数を使用して縦持ちに変換
    melted_df = df.melt(
        value_vars=rank_name_cols,
        var_name="column",
        value_name="group_name",
    )

    # group_nameがNaNまたはNoneの行を削除
    melted_df = melted_df.dropna(subset=["group_name"])

    # rank列からランク番号を抽出
    melted_df["column"] = (
        melted_df["column"].str.extract(r"column_basename_(\d+)").astype(int)
    )

    # 重複を排除
    unique_df = melted_df.drop_duplicates(subset=["column", "group_name"]).reset_index(
        drop=True
    )

    # 不要なorg_code列を削除（必要に応じて保持）
    unique_df = unique_df[["column", "group_name"]]

    return unique_df


def extract_columns(
    df: pd.DataFrame,
    columns_to_compare: list[str],
    key_columns: list[str],
    suffix="left",
):
    """
    必要な列を抽出し、指定されたサフィックスを削除して整形します。

    Args:
        df (pd.DataFrame): マージされたデータフレーム。
        columns_to_compare (list[str]): 比較対象の列名のリスト。
        key_columns (list): 一意の列名。
        suffix (str): 抽出するサフィックス（'left' または 'right'）。

    Returns:
        pd.DataFrame: 整形されたデータフレーム。
    """
    # サフィックス付きの列名を生成
    cols = [
        f"{col}_{suffix}"
        for col in columns_to_compare
        if f"{col}_{suffix}" in df.columns
    ]

    # 必要な列を抽出
    tmp_df = df[key_columns + ["flag"] + cols].copy()

    # サフィックスを削除して列名を変更
    tmp_df = tmp_df.rename(
        columns={
            f"{col}_{suffix}": col
            for col in columns_to_compare
            if f"{col}_{suffix}" in df.columns
        }
    )

    return tmp_df


def identify_differences(
    left_df: pd.DataFrame, right_df: pd.DataFrame, columns_to_compare: list[str]
) -> pd.Series:
    """
    左右のデータフレームの指定列を比較し、差分がある行を示すマスクを返します。
    NaN 同士は等価と見なします。

    Args:
        left_df (pd.DataFrame): 左側のデータフレーム。
        right_df (pd.DataFrame): 右側のデータフレーム。
        columns_to_compare (list[str]): 比較対象となる列名のリスト（接尾辞は含まない）。

    Returns:
        pd.Series: 差分がある行を示すブールマスク。
    """
    # 比較対象のカラム名を定義
    left_cols = [f"{col}_left" for col in columns_to_compare]
    right_cols = [f"{col}_right" for col in columns_to_compare]

    # 必要な列を抽出
    left_subset = left_df[left_cols]
    right_subset = right_df[right_cols]

    # カラム名を揃える
    right_subset.columns = left_cols

    # NumPy 配列として取得
    left_values = left_subset.values
    right_values = right_subset.values

    # 等しい部分のマスク
    equal_mask = left_values == right_values

    # 両方が NaN である部分のマスク
    nan_mask = np.isnan(left_values) & np.isnan(right_values)

    # 全ての等しい箇所（通常の等価 + 両方が NaN）のマスク
    combined_equal = equal_mask | nan_mask

    # 行ごとに全てのカラムが等しいかどうか
    rows_equal = np.all(combined_equal, axis=1)

    # 差分がある行を示すマスク
    diff_mask = ~rows_equal

    return pd.Series(diff_mask, index=left_df.index)


def identify_changes(
    merged_df: pd.DataFrame,
    columns_to_compare: list[str],
    key_columns: list[str],
    is_user_info=False,
):
    """
    変更点（ADD、UPDATE）を特定します。

    Args:
        merged_df (pd.DataFrame): 外部結合されたデータフレーム。
        columns_to_compare (list): 比較対象となる列名のリスト。
        key_columns (list): キーとなる列名のリスト。
        is_user_info (bool): ユーザー情報の場合はTrue。

    Returns:
        pd.DataFrame: 変更タイプが追加されたデータフレーム。
    """

    # ADD: left_only
    add_mask = merged_df["_merge"] == "left_only"
    add_df = merged_df[add_mask].copy()
    add_df["flag"] = "ADD"
    add_df = extract_columns(add_df, columns_to_compare, key_columns, "left")

    # UPDATE: both and any column differs
    both_mask = merged_df["_merge"] == "both"

    # 比較対象の列が異なるかをチェック
    diff_mask = identify_differences(
        left_df=merged_df, right_df=merged_df, columns_to_compare=columns_to_compare
    )

    update_mask = both_mask & diff_mask
    update_df = merged_df[update_mask].copy()
    update_df["flag"] = "UPDATE"
    update_df = extract_columns(update_df, columns_to_compare, key_columns, "left")

    # DISABLE: right_only and disable_flag != 1
    disable_mask = merged_df["_merge"] == "right_only"
    if is_user_info:
        # ユーザー情報の場合、新規に退職になったユーザーを特定するために、
        # department_code_rightがSYS_RETIREでないユーザーを対象とする
        disable_mask = disable_mask & (
            merged_df["department_code_right"] != "SYS_RETIRE"
        )
    else:
        # ユーザー情報でない場合、disable_flag_rightが1でないものを対象とする
        # （すでに削除済みでないものを更新対象にする）
        disable_mask = disable_mask & (merged_df["disable_flag_right"] != 1)

    disable_df = merged_df[disable_mask].copy()
    disable_df["flag"] = "UPDATE"
    disable_df = extract_columns(disable_df, columns_to_compare, key_columns, "right")

    # 特定の列のみ_right側のデータをそのまま保持
    if is_user_info:
        for col in ["disable_flag"] + [f"user_group{i}" for i in range(1, 11)]:
            disable_df[col] = ""

        already_user = disable_df["department_code"] != "SYS_RETIRE"

        # SYS_RETIREを設定すると無効化されるのでdisable_flagは空にする
        disable_df.loc[already_user, "disable_flag"] = ""
        disable_df.loc[already_user, "department_code"] = "SYS_RETIRE"
    else:
        disable_df["disable_flag"] = 1  # 無効フラグを1に設定

    # 結果を結合
    changes_df = pd.concat([add_df, update_df, disable_df], ignore_index=True)

    return changes_df


def merge_location(current_df, location_df):
    validate_location_codes(current_df, location_df)
    return pd.merge(current_df, location_df, how="inner", on="location_code")


def merge_outer_join_dataframes(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    key_columns: list[str],
):
    """
    外部結合を行います。すべての key_columns 以外の列に _left または _right のサフィックスが
    付与されているかを確認します。

    Args:
        left_df (pd.DataFrame): 左側のデータフレーム（手元のマスターデータ）。
        right_df (pd.DataFrame): 右側のデータフレーム（ダウンロードされたマスターデータ）。
        key_columns (list): 結合に使用するキーの列名。


    Returns:
        pd.DataFrame: 結合されたデータフレーム。

    Raises:
        ValueError: サフィックスがついていない列がある場合に発生します。
    """
    merged_df = pd.merge(
        left_df,
        right_df,
        on=key_columns,
        how="outer",
        suffixes=("_left", "_right"),
        indicator=True,
    )

    # サフィックスのチェック
    non_key_columns = [
        col for col in merged_df.columns if col not in key_columns and col != "_merge"
    ]
    invalid_columns = [
        col
        for col in non_key_columns
        if not (col.endswith("_left") or col.endswith("_right"))
    ]

    # サフィックスがない列があればエラーを出す
    if invalid_columns:
        raise ValueError(
            f"以下の列にサフィックスが付いていません: {', '.join(invalid_columns)}"
        )

    return merged_df


def get_file_info(file_path):
    # 保存するパスからディレクトリ名を取得する
    dirname = os.path.dirname(file_path)

    # ファイル名を取得
    basename = os.path.basename(file_path)

    root_ext_pair = os.path.splitext(basename)

    # ファイル名。拡張子なし
    basename_without_ext = root_ext_pair[0]

    # 拡張子
    ext_without_dot = root_ext_pair[1][1:]

    return dirname, basename_without_ext, ext_without_dot


def split_and_save(df: pd.DataFrame, chunk_size: int, file_path: str):
    dirname, basename_without_ext, extension = get_file_info(file_path)

    # 出力フォルダが存在しない場合は新規作成
    os.makedirs(dirname, exist_ok=True)

    # 原本を保存
    original_filename = os.path.join(
        dirname,
        f"{basename_without_ext}_original.{extension}",
    )
    df.to_excel(original_filename, index=False)
    logger.info(f"{original_filename} に原本を保存しました")

    if len(df) > chunk_size:
        # DataFrameをchunk_size件ごとに分割
        chunks = np.array_split(df, range(chunk_size, len(df), chunk_size))

        # 各チャンクを個別ファイルに保存
        for i, chunk in enumerate(chunks):
            filename = os.path.join(
                dirname,
                f"{basename_without_ext}_{str(i+1).zfill(2)}.{extension}",
            )
            chunk.to_csv(filename, index=False)
            logger.info(f"{filename} に保存しました")


def process_master_update(
    df_local: pd.DataFrame,
    df_downloaded: pd.DataFrame,
    sheet_config: SheetConfig,
    is_user_info: bool = False,
):
    """
    マスターデータの更新処理を行います。

    Args:
        df_local (pd.DataFrame): 手元のマスターデータ。
        df_downloaded (pd.DataFrame): ダウンロードされたマスターデータのデータファイル。
        sheet_config (SheetConfig): シート情報の詳細が含まれている。
        is_user_info (bool): ユーザー情報の場合はTrue。

    Returns:
        pd.DataFrame: 更新ファイル用のデータフレーム。
    """
    try:
        # 外部結合
        merged_df = merge_outer_join_dataframes(
            left_df=df_local,
            right_df=df_downloaded,
            key_columns=sheet_config.key_columns,
        )
        logger.info("Performed outer merge on key columns")

        # 変更点特定
        changes_df = identify_changes(
            merged_df=merged_df,
            columns_to_compare=sheet_config.columns_to_compare,
            key_columns=sheet_config.key_columns,  # key_columns を渡す
            is_user_info=is_user_info,
        )
        logger.info("Identified changes (ADD, UPDATE)")

        # 変更点のバリデーション
        validate_changes(changes_df)
        logger.info("Validated changes")

        # 更新ファイルは後続処理で行うため、ここではエクスポートのみ
        logger.info("Prepared changes dataframe for export")

        return changes_df
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    except pd.errors.ExcelFileError as e:
        logger.error(f"Error reading Excel file: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during processing: {e}")
        raise


def update_to_after_column(df: pd.DataFrame, target_field: str, copy_field: str):
    """フラグがUPDATEのデータのみ2列同じ値でなければならないのでフィールドをコピーする

    Args:
        df (pd.DataFrame): 修正するDF
        target_field (str): 対象のフィールド名
        copy_field (str): コピー元のフィールド名

    Returns:
        _type_: _description_
    """

    df[target_field] = ""
    mask_update = df["flag"] == "UPDATE"
    df.loc[mask_update, target_field] = df.loc[mask_update, copy_field]

    return df


def load_data_and_config(
    download_file_path: str, config_file_path: str, sheet_name: str
) -> tuple[pd.DataFrame, SheetConfig]:
    """sheetConfigとダウンロードファイルを取得する

    Args:
        download_file_path (str): ダウンロードしてきたファイルのパス
        config_file_path (str): シートコンフィグファイルのパス
        sheet_name (str): シートコンフィグファイルのシート名

    Returns:
        tuple[pd.DataFrame, SheetConfig]: _description_
    """
    # 設定ファイルから列情報を読み込み
    sheet_config = load_column_config(config_file_path, sheet_name)
    # ダウンロードされたマスターデータ読み込みと列名変更
    df = load_and_prepare_dataframe(download_file_path, sheet_config)
    return df, sheet_config


def process_user_data(
    file_paths: dict[str, dict[str, str]], org: pd.DataFrame, location_df: pd.DataFrame
) -> pd.DataFrame:
    df_local_user = load_dataframe(file_paths["user_info"])

    # 列とかの整理をする
    df_local_user = merge_location(df_local_user, location_df)

    df_local_user = pd.merge(df_local_user, org, how="inner", on="org_code")

    df_local_user["disable_flag"] = np.nan

    # ここから10行くらいデータ処理をする

    df_download_user, sheet_config = load_data_and_config(
        download_file_path=file_paths["download"]["user"],
        config_file_path=file_paths["conf"]["columns"],
        sheet_name="ユーザー情報",
    )

    update_file_user_df: pd.DataFrame = process_master_update(
        df_local=df_local_user,
        df_downloaded=df_download_user,
        sheet_config=sheet_config,
        is_user_info=True,
    )

    update_file_user_df.head()
    # データ処理ロジック
    # 処理後、メモリ解放
    # del df
    return update_file_user_df


def process_organization_data(file_paths, location_df: pd.DataFrame) -> pd.DataFrame:
    # 組織データの読み込みとマッピング情報を取得
    org_data = load_and_prepare_organization_data(file_paths)

    print("\n最終的なデータフレーム（識別子付き）:")
    print(org_data)

    df_download_org, sheet_config = load_data_and_config(
        download_file_path=file_paths["download"]["org"],
        config_file_path=file_paths["conf"]["columns"],
        sheet_name="組織",
    )

    # location_code の結合
    org_data = merge_location(org_data, location_df)

    # マスターデータの更新
    update_file_user = process_master_update(
        df_local=org_data,
        df_downloaded=df_download_org,
        sheet_config=sheet_config,
        is_user_info=True,
    )

    print(update_file_user)
    # データ処理ロジック
    # del df

    return org_data


def process_location_data(file_paths):
    df_local_location = load_dataframe(file_paths["location"])
    df_local_location = df_local_location.rename(
        columns={"事業所コード": "location_code", "事業所名": "location_name"}
    )
    df_local_location["location_identifier"] = (
        df_local_location["location_code"] + "_" + df_local_location["location_name"]
    )

    df_local_location["disable_flag"] = np.nan

    df_download_location, sheet_config = load_data_and_config(
        download_file_path=file_paths["location"],
        config_file_path=file_paths["conf"]["columns"],
        sheet_name="事業所",
    )

    merge_location = process_master_update(
        df_local=df_local_location,
        df_downloaded=df_download_location,
        sheet_config=sheet_config,
        is_user_info=True,
    )

    merge_location = update_to_after_column(
        merge_location, "location_after", "location_identifier"
    )

    # 順番を整える
    merge_location = merge_location[sheet_config.column_names]

    split_and_save(merge_location, 100, file_paths["output"]["location"])

    # 戻すのは更新ように作成されたファイルではなく、実データを戻す
    return df_local_location


def process_usergroup_data(file_paths, df_user: pd.DataFrame):
    # 縦持ちに変換されたデータフレーム
    reshaped_df = reshape_rank_names(
        df_user, "user_group", start_rank=3, end_rank=5
    )  # 必要に応じて範囲を調整

    # group_name, dllの2列が返ってくる
    reshaped_df["disable_flag"] = np.nan

    # 列名をダウンロードしてきたファイルに合わせる（関数でマッチングさせるために）

    df_download_usergroup, sheet_config = load_data_and_config(
        download_file_path=file_paths["download"]["usergroup"],
        config_file_path=file_paths["conf"]["columns"],
        sheet_name="ユーザーグループ",
    )

    update_df = process_master_update(
        df_local=reshaped_df,
        df_downloaded=df_download_usergroup,
        sheet_config=sheet_config,
        is_user_info=True,
    )

    # 重複する組織名が存在する場合のアラート（事前にチェックしてるからないはずだけど）
    duplicate_group_names = reshaped_df["group_name"].duplicated(keep=False)
    if duplicate_group_names.any():
        duplicate_names = reshaped_df.loc[duplicate_group_names, "group_name"].unique()
        for name in duplicate_names:
            alert_msg = f"重複した組織名 '{name}' が存在します。識別子が正しく付与されているか確認してください。"

            logger.warning(alert_msg)

    print(update_df)
    # データ処理ロジック
    # del df
    update_df.to_excel("完成.xlsx")
