# user_data_preprocessor.py
"""
WEVOXシステムのユーザーデータ前処理を行うモジュール。
CSVProcessorを使用してCSVファイルを読み込み、
特定の業務要件に基づいてデータの結合と前処理を実行する。
"""

from dataclasses import dataclass
from typing import Optional, Dict
import pandas as pd

from csv_processor import CSVProcessor


@dataclass
class UserDataMergeConfig:
    """ユーザーデータのマージ設定を保持するデータクラス"""
    
    user_title_key: str = 'title_code'  # userとtitleの結合キー
    user_location_key: str = 'location_code'  # userとlocationの結合キー
    required_columns: dict[str, list[str]] = None  # 各CSVファイルの必須カラム
    
    def __post_init__(self):
        if self.required_columns is None:
            self.required_columns = {
                'user': ['user_code', self.user_title_key, self.user_location_key],
                'title': [self.user_title_key],
                'location': [self.user_location_key]
            }


class UserDataPreprocessor:
    """WEVOXシステムのユーザーデータ前処理を行うクラス"""
    
    def __init__(
        self,
        csv_processor: CSVProcessor,
        merge_config: Optional[UserDataMergeConfig] = None
    ):
        """
        Parameters:
        - csv_processor (CSVProcessor): CSVファイル処理用のインスタンス
        - merge_config (Optional[UserDataMergeConfig]): マージ設定
        """
        self.csv_processor = csv_processor
        self.merge_config = merge_config or UserDataMergeConfig()
        self.processed_dfs: Dict[str, pd.DataFrame] = {}

    def validate_required_columns(self) -> list[str]:
        """
        必須カラムの存在チェック
        
        Returns:
        - list[str]: エラーメッセージのリスト
        """
        errors = []
        
        for file_name, required_cols in self.merge_config.required_columns.items():
            df = self.csv_processor.get_processed_dataframe(file_name)
            if df is None:
                errors.append(f"{file_name}.csvが見つかりません。")
                continue
                
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                errors.append(
                    f"{file_name}.csvに必須カラム{', '.join(missing_cols)}が"
                    "存在しません。"
                )
        
        return errors

    def preprocess_user_data(self) -> pd.DataFrame:
        """
        ユーザーデータの前処理を実行
        
        Returns:
        - pd.DataFrame: 前処理済みのユーザーDataFrame
        
        Raises:
        - ValueError: 必須カラムが存在しない場合
        """
        # 必須カラムのバリデーション
        errors = self.validate_required_columns()
        if errors:
            raise ValueError("\n".join(errors))
        
        # 各DataFrameを取得
        user_df = self.csv_processor.get_processed_dataframe('user')
        title_df = self.csv_processor.get_processed_dataframe('title')
        location_df = self.csv_processor.get_processed_dataframe('location')
        
        # titleとの結合
        user_df = pd.merge(
            user_df,
            title_df,
            on=self.merge_config.user_title_key,
            how='left',
            suffixes=('', '_title')
        )
        
        # locationとの結合
        user_df = pd.merge(
            user_df,
            location_df,
            on=self.merge_config.user_location_key,
            how='left',
            suffixes=('', '_location')
        )
        
        # 結合後の基本的なバリデーション
        null_titles = user_df[user_df[self.merge_config.user_title_key].isnull()]
        if not null_titles.empty:
            print(f"Warning: {len(null_titles)}件の未マッチの役職コードが存在します。")
            
        null_locations = user_df[user_df[self.merge_config.user_location_key].isnull()]
        if not null_locations.empty:
            print(f"Warning: {len(null_locations)}件の未マッチの所在地コードが存在します。")
        
        self.processed_dfs['user_processed'] = user_df
        return user_df

    def export_processed_data(self, output_path: str) -> None:
        """
        処理済みデータをExcelファイルとして出力
        
        Parameters:
        - output_path (str): 出力先のパス
        """
        if not self.processed_dfs:
            raise ValueError("先にpreprocess_user_data()を実行してください。")
            
        with pd.ExcelWriter(output_path) as writer:
            for sheet_name, df in self.processed_dfs.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)


# 使用例
if __name__ == "__main__":
    # CSVProcessorの初期化
    csv_processor = CSVProcessor(
        folder_path="path/to/csv/folder",
        config_path="path/to/config.xlsx"
    )
    
    # カスタム設定の作成（必要に応じて）
    custom_config = UserDataMergeConfig(
        user_title_key='title_code',
        user_location_key='location_code',
        required_columns={
            'user': ['user_code', 'title_code', 'location_code'],
            'title': ['title_code', 'title_name'],
            'location': ['location_code', 'location_name']
        }
    )
    
    # UserDataPreprocessorの初期化と実行
    preprocessor = UserDataPreprocessor(csv_processor, custom_config)
    try:
        processed_df = preprocessor.preprocess_user_data()
        preprocessor.export_processed_data("processed_user_data.xlsx")
        print("データの前処理が完了しました。")
    except ValueError as e:
        print(f"エラーが発生しました：\n{e}")