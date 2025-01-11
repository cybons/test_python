# user_processor.py
from dataclasses import dataclass, field
from logging import getLogger

import pandas as pd
from config import Config
from models.data_model import ColumnRenameError, UserProcessor
from utils import save_dfs_to_excel_with_tables

logger = getLogger(__name__)


def rename_columns(df, column_mapping):
    return df.rename(columns=column_mapping)


@dataclass
class ExclusionUsers:
    filter_column: str
    exclusion_key: str
    values: list[str] = field(default_factory=list)


def filter_exclusions(
    df: pd.DataFrame, exclusions: list[ExclusionUsers]
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """
    DataFrameから指定の除外条件に基づき行を除外し、除外された行を分けて返す関数

    Parameters:
    - df: pd.DataFrame - 処理対象のデータフレーム
    - exclusions: List[ExclusionUsers] - 除外する条件を指定したリスト

    Returns:
    - Tuple containing:
        - pd.DataFrame - 除外対象外の行を含む新しいデータフレーム
        - Dict[str, pd.DataFrame] - 除外条件ごとに該当する行のデータフレームを保持する辞書
    """

    # 初期のマスクを全てTrueにして作成
    mask = pd.Series(True, index=df.index)
    exclusion_dfs: dict[str, pd.DataFrame] = {}

    # 各除外条件ごとに処理
    for item in exclusions:
        if item.filter_column not in df.columns:
            raise ValueError(f"Column '{item.filter_column}' not found in DataFrame.")

        # 条件に一致する行を選ぶマスクを作成
        exclusion_mask = df[item.filter_column].isin(item.values)

        # 除外行を別データフレームとして保存
        exclusion_dfs[item.exclusion_key] = df[exclusion_mask].copy()

        # 除外対象をメインマスクから除外
        mask &= ~exclusion_mask

    # 除外されていない行のみを残したデータフレームと、除外行の辞書を返す
    return df[mask].copy(), exclusion_dfs


def merge_additional_info(df, additional_dfs, on_key):
    for key, additional_df in additional_dfs.items():
        df = df.merge(additional_df, on=on_key, how="left", suffixes=("", f"_{key}"))
    return df


def label_age(df, age_bins, age_labels, age_column="age"):
    df["age_group"] = pd.cut(df[age_column], bins=age_bins, labels=age_labels)
    return df


def label_employment_type(
    df, dispatch_col="is_dispatch", new_employee_col="is_new_employee"
):
    df["employment_type"] = "Regular"
    df.loc[df[dispatch_col] is True, "employment_type"] = "Dispatch"
    df.loc[df[new_employee_col] is True, "employment_type"] = "New Employee"
    return df


# 他の必要な関数もここに追加
# main.py
# from user_processor import (
#     filter_exclusions,
#     label_age,
#     label_employment_type,
#     merge_additional_info,
#     rename_columns,
# )

# データの読み込み


def main():
    # 設定の読み込み
    config = Config("config.yaml")

    # データの読み込み
    users_df = pd.read_csv("users.csv")
    employees_df = pd.read_csv("employees.csv")
    departments_df = pd.read_csv("departments.csv")

    # 追加情報の読み込み
    location_df = pd.read_csv("locations.csv")
    organization_df = pd.read_csv("organizations.csv")
    position_df = pd.read_csv("positions.csv")

    # 列名の変更
    # column_mapping = {
    #     "産休": "maternity_leave",
    #     "育休": "parental_leave",
    #     "休職": "leave_of_absence",
    #     # 他の列名マッピング
    # }
    # user_df = rename_columns(user_df, column_mapping)

    # 除外条件の設定
    exclusions = [
        ExclusionUsers(
            column_name="maternity_leave", key="user_code", values=["12345", "11111"]
        ),
        ExclusionUsers(
            column_name="parental_leave", key="user_code", values=["44444", "33333"]
        ),
        ExclusionUsers(
            column_name="leave_of_absence", key="user_code", values=["55555", "66666"]
        ),
        ExclusionUsers(
            column_name="position", key="user_code", values=["特定役職1", "特定役職2"]
        ),
    ]

    # フィルタリングと除外データフレームの取得
    filtered_user_df, excluded_dfs = filter_exclusions(users_df, exclusions)

    # 各データフレームのプロセス情報
    processors = [
        {
            "df": users_df,
            "name": "users",
            "additional_dfs": {
                "location": location_df,
                "organization": organization_df,
                "position": position_df,
            },
            "on_key": "user_id",
        },
        {
            "df": employees_df,
            "name": "employees",
            "additional_dfs": {
                "location": location_df,
                "organization": organization_df,
                "position": position_df,
            },
            "on_key": "employee_id",
        },
        {
            "df": departments_df,
            "name": "departments",
            "additional_dfs": {
                "location": location_df,
                "organization": organization_df,
                "position": position_df,
            },
            "on_key": "department_id",
        },
    ]
    # 追加情報のマージ
    additional_dfs = {
        "location": location_df,
        "organization": organization_df,
        "position": position_df,
    }
    filtered_user_df = merge_additional_info(
        filtered_user_df, additional_dfs, on_key="user_id"
    )

    # ラベリング
    age_bins = [0, 25, 35, 45, 60, 100]
    age_labels = ["<25", "25-34", "35-44", "45-59", "60+"]
    filtered_user_df = label_age(filtered_user_df, age_bins, age_labels)

    filtered_user_df = label_employment_type(filtered_user_df)

    # 結果の確認
    print(filtered_user_df.head())

    save_dfs_to_excel_with_tables(excluded_dfs, ".", "filelist")

    for processor_info in processors:
        try:
            with UserProcessor(
                processor_info["df"], config, processor_info["name"]
            ) as processor:
                processor.rename_columns().filter_exclusions().merge_additional_info(
                    additional_dfs=processor_info["additional_dfs"],
                    on_key=processor_info["on_key"],
                ).label_age().label_employment_type()

                processed_df = processor.get_processed_df()
                excluded_dfs = processor.get_excluded_dfs()

                # 結果の確認（例として表示）
                logger.info(f"Processed DataFrame: {processor_info['name']}")
                print(processed_df.head())

                # 除外データフレームの保存
                for key, df in excluded_dfs.items():
                    output_filename = f'excluded_{processor_info["name"]}_{key}.csv'
                    df.to_csv(output_filename, index=False)
                    logger.info(f"Excluded data saved to {output_filename}")

        except ColumnRenameError as e:
            logger.error(f"Failed to rename columns for {processor_info['name']}: {e}")
            # 処理を中断する場合は以下を有効にします
            # raise
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while processing {processor_info['name']}: {e}"
            )
            # 処理を中断する場合は以下を有効にします
            # raise
