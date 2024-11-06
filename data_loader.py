import glob
import json
import os
from logging import getLogger

import pandas as pd
import yaml
from data_model import SheetConfig
from organization import create_organization

logger = getLogger(__name__)


def find_latest_file(file_path: str):
    """
    特定のフォルダ内でパターンに一致する最新のファイルを取得します。

    Args:
        file_path (str): ファイル名のパターン（ワイルドカードを含む）。

    Returns:
        str: 最新のファイルのパス。
    """

    matching_files = glob.glob(file_path)
    if not matching_files:
        raise FileNotFoundError(f"No files found for pattern: {file_path}")

    # ファイル名でソートし、最新のファイルを選択
    latest_file = max(matching_files, key=os.path.getmtime)
    return latest_file


def load_dataframe(path: str, encoding="cp932", sheet_name=None) -> pd.DataFrame:
    """指定されたパスからファイルを読み込み、データフレーム型で返す。

    Args:
        path (str): ファイルパス
        encoding (str, optional): txt, csv, tsvの場合のエンコード. Defaults to "cp932".
        sheet_name (_type_, optional): Excelを読み込む場合のシート名. Defaults to None.

    Raises:
        ValueError: ファイルが見つからない場合にエラーを出す

    Returns:
        データフレーム: _description_
    """

    file_path = find_latest_file(path)

    if file_path.endswith(".xlsx"):
        if sheet_name:
            return pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)

        return pd.read_excel(file_path, dtype=str)

    elif file_path.endswith(".txt"):
        return pd.read_csv(file_path, sep="\t", encoding=encoding, dtype=str)

    else:
        raise ValueError(f"Unsupported file type: {file_path}")


def load_column_config(column_config_file_path: str, sheet_name: str) -> SheetConfig:
    """
    指定されたExcelファイルとシート名から列情報を取得します。

    Args
    -------
        config_file_path (str): 設定ファイルのパス。
        sheet_name (str): 列情報が含まれるシート名。

    Returns
    -------
        SheetConfig: シートの詳細を返す
    """

    # 設定ファイルの読み込み
    config_df = pd.read_excel(
        find_latest_file(column_config_file_path), sheet_name, dtype=str
    )

    # 全列名を取得
    column_names = config_df["列名"].tolist()

    # キー列を取得
    key_columns = config_df[config_df["キー"].notna()]["列名"].tolist()

    # 削除列を取得
    drop_cols = config_df[config_df["削除"].notna()]["列名"].tolist()

    # 比較対象列を取得（全列からキーと削除列を除外）
    columns_to_compare = [
        col for col in column_names if col not in key_columns + drop_cols
    ]

    return SheetConfig(column_names, key_columns, drop_cols, columns_to_compare)


def load_and_prepare_dataframe(
    file_path: str, sheet_config: SheetConfig
) -> pd.DataFrame:
    """指定されたパスのコンフィグファイルを読み込み、sheet_configに基づいて前処理を実施する

    Args:
        file_path (str): ファイルパス
        sheet_config (SheetConfig): 読み込むファイルに対応するキー情報や削除対象カラム情報など

    Returns:
        pd.DataFrame: 前処理を施したデータフレーム
    """
    df = pd.read_excel(
        find_latest_file(file_path),
        header=0,
        names=sheet_config.column_names,
        dtype=str,
    )

    # 指定された列を除外
    if sheet_config.drop_cols:
        df = df.drop(columns=sheet_config.drop_cols, errors="ignore")
    logger.info(f"データの読み込みと前処理が完了しました {file_path}")
    return df


def load_and_prepare_organization_data(file_paths) -> pd.DataFrame:
    """
    組織データとマッピング情報（略称）を読み込み、組織情報を作成します。

    Args:
        file_paths (dict): ファイルパスの辞書。

    Returns:
        pd.DataFrame: 組織情報データ。
    """
    # csvの読み込み
    df = load_dataframe(file_paths["organization"])

    # マッピング情報を読み込み
    df_mapping = load_dataframe(file_paths["conf"]["mapping"])

    # 組織情報を作成
    org_data = create_organization(df, df_mapping=df_mapping)

    return org_data


def resolve_paths(config: dict, base_path: str) -> dict:
    """パス階層の辞書内で相対パスを絶対パスに変換します."""
    base_dir = os.path.dirname(base_path)
    extensions = [".csv", ".xlsx", ".txt", ".tsv"]

    def resolve_relative_path(value):
        # 拡張子リストでチェック
        if isinstance(value, str) and any(ext in value for ext in extensions):
            return os.path.abspath(os.path.join(base_dir, value))
        elif isinstance(value, dict):
            return {k: resolve_relative_path(v) for k, v in value.items()}
        else:
            return value

    return {k: resolve_relative_path(v) for k, v in config.items()}


def load_config(file_path="config.yaml", encoding="utf8") -> dict:
    """_summary_

    Args:
        file_path (str, optional): ファイルパスを指定する. Defaults to "config.yaml".
        encoding (str, optional): エンコードを指定する. Defaults to "utf8".

    Raises:
        ValueError: 型がdictではない場合エラーを出力する

    Returns:
        dict: 設定の値が辞書型で返る
    """
    ext_without_dot = os.path.splitext(file_path)[1][1:]

    with open(file_path, "r", encoding=encoding) as file:
        if ext_without_dot == "yaml":
            config = yaml.safe_load(file)
        elif ext_without_dot == "json":
            config = json.load(file)

    if isinstance(config, dict):
        return resolve_paths(config, file_path)
    else:
        raise ValueError("データが辞書型ではありません。")


# base_dir = os.path.dirname(__file__)
# config = load_config(os.path.join(base_dir, "conf", "file_path.yaml"))
# pprint.pprint(config)
