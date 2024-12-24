import re
from typing import List, Tuple
import pandas as pd

class Validator:
    def __init__(self, system_data: pd.DataFrame):
        self.system_data = system_data  # システムデータ (DataFrame)
        self.errors: List[Tuple[int, str, str]] = []  # エラーを蓄積するリスト
        # 組織名に全角カナ、全角記号、全角アルファベットを検出する正規表現
        self.org_name_pattern = re.compile(r'[ァ-ンＡ-Ｚａ-ｚ\uFF01-\uFF0F\uFF1A-\uFF20\uFF3B-\uFF40\uFF5B-\uFF60]')

        # システムデータのユーザーIDと名前の辞書を事前に作成
        self.system_data_dict = self.system_data.set_index('user_id')['name'].to_dict()

    def validate(self, df: pd.DataFrame) -> List[Tuple[int, str, str]]:
        """全てのバリデートを実行"""
        self.errors.clear()  # エラーを初期化
        self._validate_user_exists(df)
        self._validate_name_match(df)
        self._validate_org_name(df)
        return self.errors

    def _add_errors(self, df: pd.DataFrame, condition: pd.Series, column_name: str, 
                   error_message_func) -> None:
        """共通エラー登録処理"""
        error_indices = condition[condition].index
        for idx in error_indices:
            self.errors.append((idx, column_name, error_message_func(idx)))

    def _validate_user_exists(self, df: pd.DataFrame) -> None:
        """ユーザーが存在するか確認 (ベクトル化)"""
        invalid_users = ~df['user_id'].isin(self.system_data['user_id'])
        self._add_errors(
            df,
            invalid_users,
            "user_id",
            lambda idx: f"ユーザー {df.at[idx, 'user_id']} が存在しません"
        )

    def _validate_name_match(self, df: pd.DataFrame) -> None:
        """氏名が一致するか確認 (ベクトル化)"""
        name_series = df['user_id'].map(self.system_data_dict)
        mismatched_names = df['user_id'].isin(self.system_data_dict) & (df['name'] != name_series)
        self._add_errors(
            df,
            mismatched_names,
            "name",
            lambda idx: f"氏名が一致しません: {df.at[idx, 'name']}"
        )

    def _validate_org_name(self, df: pd.DataFrame) -> None:
        """組織名に全角かな・記号が混ざっていないか確認 (ベクトル化)"""
        invalid_orgs = df['org_name'].apply(
            lambda x: bool(self.org_name_pattern.search(x)) if pd.notnull(x) else False
        )
        self._add_errors(
            df,
            invalid_orgs,
            "org_name",
            lambda idx: f"組織名に全角かなが含まれています: {df.at[idx, 'org_name']}"
        )