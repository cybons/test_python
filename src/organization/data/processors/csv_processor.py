# csv_processor.py
"""
CSVファイルの読み込みと前処理を行うモジュール。
Excelコンフィグファイルに基づいて列のリネームやスキップを実行する。
"""

import os
from typing import Optional

import pandas as pd


class ConfigReader:
    """Excelコンフィグファイルを読み込み、CSVの列設定を管理するクラス"""

    def __init__(self, config_path: str):
        """
        Parameters:
        - config_path (str): コンフィグExcelファイルのパス
        """
        self.config_path = config_path
        self.config_dict: dict[str, dict[str, dict]] = {}
        self._read_config()

    def _read_config(self) -> None:
        """Excelファイルから各シートの設定を読み込む"""
        excel_file = pd.ExcelFile(self.config_path)

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)

            # 空の行を除外
            df = df.dropna(how="all")

            # リネーム用の辞書を作成（NaNを除外）
            rename_dict = df.iloc[:, [0, 1]].dropna(subset=[df.columns[1]])
            rename_mapping = dict(zip(rename_dict.iloc[:, 0], rename_dict.iloc[:, 1]))

            # スキップする列のリストを作成
            skip_columns = df[df.iloc[:, 2] == "○"].iloc[:, 0].tolist()

            self.config_dict[sheet_name] = {
                "rename": rename_mapping,
                "skip": skip_columns,
            }

    def get_config(self, file_name: str) -> Optional[dict[str, dict]]:
        """
        指定されたファイル名の設定を取得

        Parameters:
        - file_name (str): 設定を取得したいファイル名（拡張子なし）

        Returns:
        - Optional[Dict[str, dict]]: ファイルの設定情報。存在しない場合はNone
        """
        return self.config_dict.get(file_name)


class CSVProcessor:
    """CSVファイルの読み込みと前処理を行うクラス"""

    def __init__(self, folder_path: str, config_path: str, encoding: str = "utf-8"):
        """
        Parameters:
        - folder_path (str): CSVファイルが格納されているフォルダのパス
        - config_path (str): コンフィグExcelファイルのパス
        - encoding (str): CSVファイルの文字コード（デフォルトは 'utf-8'）
        """
        self.folder_path = folder_path
        self.encoding = encoding
        self.config_reader = ConfigReader(config_path)
        self.csv_dict: dict[str, pd.DataFrame] = {}
        self._import_and_process_csvs()

    def _import_and_process_csvs(self) -> None:
        """
        フォルダ内のCSVファイルを読み込み、設定に基づいて前処理を行う
        """
        for filename in os.listdir(self.folder_path):
            if filename.lower().endswith(".csv"):
                file_path = os.path.join(self.folder_path, filename)
                file_name = os.path.splitext(filename)[0]

                try:
                    # CSVファイルの読み込み
                    df = pd.read_csv(file_path, encoding=self.encoding, dtype=str)

                    # コンフィグに基づいて前処理
                    df = self._apply_config(df, file_name)

                    self.csv_dict[file_name] = df

                except Exception as e:
                    print(f"Error processing {filename}: {e}")

    def _apply_config(self, df: pd.DataFrame, file_name: str) -> pd.DataFrame:
        """
        データフレームにコンフィグの設定を適用

        Parameters:
        - df (pd.DataFrame): 処理対象のDataFrame
        - file_name (str): ファイル名

        Returns:
        - pd.DataFrame: 処理後のDataFrame
        """
        config = self.config_reader.get_config(file_name)
        if config:
            # 列のリネーム
            if config["rename"]:
                df = df.rename(columns=config["rename"])

            # 不要な列の削除
            if config["skip"]:
                df = df.drop(columns=config["skip"], errors="ignore")

        return df

    def get_processed_dataframe(self, file_name: str) -> Optional[pd.DataFrame]:
        """
        処理済みのDataFrameを取得

        Parameters:
        - file_name (str): 取得したいファイル名（拡張子なし）

        Returns:
        - Optional[pd.DataFrame]: 処理済みのDataFrame。存在しない場合はNone
        """
        return self.csv_dict.get(file_name)

    def merge_dataframes(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        key: str or list[str],
        how: str = "inner",
    ) -> pd.DataFrame:
        """
        2つのDataFrameをマージ

        Parameters:
        - df1 (pd.DataFrame): マージする最初のDataFrame
        - df2 (pd.DataFrame): マージする2つ目のDataFrame
        - key (str or list[str]): マージに使用するキー
        - how (str): マージ方法

        Returns:
        - pd.DataFrame: マージ後のDataFrame
        """
        return pd.merge(df1, df2, on=key, how=how)

    def preprocess_and_merge(
        self,
        preprocess_keys: list[str],
        single_key: str,
        merge_key: str or list[str],
        how: str = "inner",
    ) -> pd.DataFrame:
        """
        複数のDataFrameを順次マージ

        Parameters:
        - preprocess_keys (list[str]): 前処理用のファイル名リスト
        - single_key (str): 最後にマージするファイル名
        - merge_key (str or list[str]): マージに使用するキー
        - how (str): マージ方法

        Returns:
        - pd.DataFrame: 最終的なマージ結果
        """
        if not preprocess_keys:
            raise ValueError("preprocess_keysには少なくとも1つのキーが必要です。")

        # 最初のDataFrameを取得
        result_df = self.csv_dict.get(preprocess_keys[0])
        if result_df is None:
            raise KeyError(f"{preprocess_keys[0]}が見つかりません。")

        # 残りのファイルを順次マージ
        for key in preprocess_keys[1:]:
            df = self.csv_dict.get(key)
            if df is None:
                raise KeyError(f"{key}が見つかりません。")
            result_df = self.merge_dataframes(result_df, df, key=merge_key, how=how)

        # 最後のファイルとマージ
        single_df = self.csv_dict.get(single_key)
        if single_df is None:
            raise KeyError(f"{single_key}が見つかりません。")

        return self.merge_dataframes(result_df, single_df, key=merge_key, how=how)


# 使用例
if __name__ == "__main__":
    # CSVファイルとコンフィグファイルのパスを設定
    csv_folder = "path/to/csv/folder"
    config_file = "path/to/config.xlsx"

    # CSVProcessorのインスタンス作成
    processor = CSVProcessor(csv_folder, config_file)

    # 処理済みのDataFrameを取得
    df = processor.get_processed_dataframe("example_file")
    if df is not None:
        print(df.head())
