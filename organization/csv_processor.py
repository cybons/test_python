# csv_processor.py

import os
import pandas as pd
from typing import Dict, List, Optional

class CSVProcessor:
    def __init__(
        self, 
        folder_path: str, 
        encoding: str = 'utf-8', 
        column_config: Optional[Dict[str, Dict[str, List[str]]]] = None
    ):
        """
        CSVProcessorの初期化

        Parameters:
        - folder_path (str): CSVファイルが格納されているフォルダのパス
        - encoding (str): CSVファイルの文字コード（デフォルトは 'utf-8'）
        - column_config (dict, optional): 各CSVファイルの列名設定
        """
        self.folder_path = folder_path
        self.encoding = encoding
        self.column_config = column_config
        self.csv_dict = self.import_csvs_as_dict(column_config=self.column_config)

    def import_csvs_as_dict(
        self, 
        column_config: Optional[Dict[str, Dict[str, List[str]]]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        指定されたフォルダ内のCSVファイルをすべて読み込み、ファイル名をキーとした辞書を返す。
        列名のリネームやスキップも行う。

        Parameters:
        - column_config (dict, optional): 各CSVファイルの列名設定。

        Returns:
        - dict: ファイル名（拡張子なし）をキー、DataFrameを値とする辞書
        """
        csv_dict = {}
        for filename in os.listdir(self.folder_path):
            if filename.endswith('.csv'):
                filepath = os.path.join(self.folder_path, filename)
                key = os.path.splitext(filename)[0]
                try:
                    df = pd.read_csv(filepath, encoding=self.encoding, dtype=str)  # すべての列を文字列型として読み込む
                    
                    # 列名のリネームとスキップの適用
                    if column_config and key in column_config:
                        config = column_config[key]
                        
                        # リネーム
                        if 'rename' in config:
                            df.rename(columns=config['rename'], inplace=True)
                        
                        # スキップ（削除）
                        if 'skip' in config:
                            df.drop(columns=config['skip'], inplace=True, errors='ignore')
                    
                    csv_dict[key] = df
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
        return csv_dict

    @staticmethod
    def merge_dataframes(df1: pd.DataFrame, df2: pd.DataFrame, key: str or List[str], how: str = 'inner') -> pd.DataFrame:
        """
        2つのDataFrameを指定したキーでマージする。

        Parameters:
        - df1 (pd.DataFrame): マージする最初のDataFrame
        - df2 (pd.DataFrame): マージする2つ目のDataFrame
        - key (str or list of str): マージに使用するキー
        - how (str): マージ方法（'inner', 'left', 'right', 'outer'）

        Returns:
        - pd.DataFrame: マージされたDataFrame
        """
        merged_df = pd.merge(df1, df2, on=key, how=how)
        return merged_df

    def preprocess_and_merge(
        self,
        preprocess_keys: List[str],
        single_key: str,
        merge_key: str or List[str],
        how: str = 'inner'
    ) -> pd.DataFrame:
        """
        前処理用の複数ファイルをマージし、単体ファイルと最終的にマージする。

        Parameters:
        - preprocess_keys (list of str): 前処理用のCSVファイル名（辞書のキー）
        - single_key (str): 単体で処理するCSVファイル名（辞書のキー）
        - merge_key (str or list of str): マージに使用するキー
        - how (str): マージ方法（デフォルトは 'inner'）

        Returns:
        - pd.DataFrame: 最終的にマージされたDataFrame
        """
        if not preprocess_keys:
            raise ValueError("preprocess_keysには少なくとも1つのキーが必要です。")

        # 最初の前処理ファイルで開始
        preprocessed_df = self.csv_dict.get(preprocess_keys[0])
        if preprocessed_df is None:
            raise KeyError(f"{preprocess_keys[0]} が見つかりません。")

        # 残りの前処理ファイルを順次マージ
        for key in preprocess_keys[1:]:
            df = self.csv_dict.get(key)
            if df is None:
                raise KeyError(f"{key} が見つかりません。")
            preprocessed_df = self.merge_dataframes(preprocessed_df, df, key=merge_key, how=how)

        # 単体ファイルの取得
        single_df = self.csv_dict.get(single_key)
        if single_df is None:
            raise KeyError(f"{single_key} が見つかりません。")

        # 最終的なマージ
        final_df = self.merge_dataframes(preprocessed_df, single_df, key=merge_key, how=how)
        return final_df
        
        
 # main.py

from csv_processor import CSVProcessor

def main():
    # CSVファイルが格納されているフォルダのパス
    folder_path = 'path/to/your/csv_folder'

    # 列名の設定
    column_config = {
        'file1': {
            'rename': {'旧列名1': '新列名1', '旧列名2': '新列名2'},
            'skip': ['スキップ列1', 'スキップ列2']
        },
        'file2': {
            'rename': {'旧列名A': '新列名A'},
            'skip': ['スキップ列A']
        },
        # 他のファイルの設定も追加可能
    }

    # CSVProcessorのインスタンス作成（column_configを渡す）
    processor = CSVProcessor(folder_path, encoding='utf-8', column_config=column_config)

    # 前処理用の4つのファイル名（拡張子なし）
    preprocess_keys = ['file1', 'file2', 'file3', 'file4']

    # 単体で処理する1つのファイル名（拡張子なし）
    single_key = 'file5'

    # マージに使用するキー
    merge_key = 'your_key'

    # データのマージ
    try:
        final_df = processor.preprocess_and_merge(preprocess_keys, single_key, merge_key)
        # 結果の確認
        print(final_df.head())
    except Exception as e:
        print(f"Error during processing: {e}")

if __name__ == "__main__":
    main()