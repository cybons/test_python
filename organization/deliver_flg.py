from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path

@dataclass
class DeliverFlagConfig:
    """配信フラグの設定に関する設定を保持するクラス"""
    application_path: str  # 申請書のパス
    leave_files: Dict[str, str]  # 休職者等のファイルパスを保持する辞書
    current_deliver_flag_path: Optional[str] = None  # 現在のdeliver_flag.xlsxのパス（差分更新用）
    output_path: str = "deliver_flag.xlsx"  # 出力先のパス

class DeliverFlagProcessor:
    """配信フラグの処理を行うクラス"""
    
    def __init__(self, config: DeliverFlagConfig):
        self.config = config
        self.processed_users: Dict[str, bool] = {}  # メールアドレスとフラグを保持
        
    def process(self) -> None:
        """メイン処理を実行"""
        # 1. 申請書からの基本データ処理
        self._process_application_file()
        
        # 2. 休職者等の処理
        self._process_leave_files()
        
        # 3. 現在のフラグとの差分確認（指定されている場合）
        if self.config.current_deliver_flag_path:
            self._check_differences()
        
        # 4. 結果の出力
        self._save_results()
    
    def _process_application_file(self) -> None:
        """申請書の処理"""
        # Excelファイルの全シートを読み込み
        excel_file = pd.ExcelFile(self.config.application_path)
        
        # 配信組織シートの処理
        org_df = pd.read_excel(excel_file, sheet_name="配信組織")
        self._process_org_sheet(org_df)
        
        # 個別登録シートの処理（配信組織シート以外の全シート）
        for sheet_name in excel_file.sheet_names:
            if sheet_name != "配信組織":
                individual_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                self._process_individual_sheet(individual_df)
    
    def _process_org_sheet(self, df: pd.DataFrame) -> None:
        """配信組織シートの処理"""
        for _, row in df.iterrows():
            org_code = row['組織コード']
            include_sub = row['配下含む']
            employment_conditions = {
                '正社員': row['正社員含む'],
                '派遣社員': row['派遣社員含む'],
                '契約社員': row['契約社員含む']
            }
            
            # 組織に所属するユーザーの取得とフラグ設定
            users = self._get_users_in_org(org_code, include_sub, employment_conditions)
            for email in users:
                if email not in self.processed_users:  # まだ処理されていないユーザーのみ
                    self.processed_users[email] = True
    
    def _process_individual_sheet(self, df: pd.DataFrame) -> None:
        """個別登録シートの処理"""
        # 社員番号と配信フラグの列を確認
        if '社員番号' in df.columns and '配信フラグ' in df.columns:
            for _, row in df.iterrows():
                if row['配信フラグ'] == 'いいえ':
                    email = self._get_email_from_id(row['社員番号'])
                    if email:
                        self.processed_users[email] = False
    
    def _process_leave_files(self) -> None:
        """休職者等のファイル処理"""
        for file_type, file_path in self.config.leave_files.items():
            if not Path(file_path).exists():
                continue
                
            df = pd.read_excel(file_path)
            for email in self._get_emails_from_df(df):
                self.processed_users[email] = False
    
    def _check_differences(self) -> None:
        """現在のフラグとの差分確認"""
        if not Path(self.config.current_deliver_flag_path).exists():
            return
            
        current_df = pd.read_excel(self.config.current_deliver_flag_path)
        current_flags = dict(zip(current_df['メールアドレス'], current_df['配信']))
        
        # 現在のフラグと新しいフラグを比較
        updated_users = {}
        for email, new_flag in self.processed_users.items():
            if email not in current_flags or current_flags[email] != new_flag:
                updated_users[email] = new_flag
        
        self.processed_users = updated_users
    
    def _save_results(self) -> None:
        """結果をExcelファイルとして保存"""
        df = pd.DataFrame({
            'メールアドレス': list(self.processed_users.keys()),
            '配信': [str(flag).upper() for flag in self.processed_users.values()]
        })
        df.to_excel(self.config.output_path, index=False)
    
    def _get_users_in_org(self, org_code: str, include_sub: bool, 
                         employment_conditions: Dict[str, bool]) -> List[str]:
        """
        組織に所属するユーザーのメールアドレスを取得
        
        Note: この実装は仮のものです。実際の実装では組織構造とユーザー情報を
        参照するデータベースやファイルからデータを取得する必要があります。
        """
        # TODO: 実際のデータソースからユーザー情報を取得する実装
        return []
    
    def _get_email_from_id(self, employee_id: str) -> Optional[str]:
        """
        社員番号からメールアドレスを取得
        
        Note: この実装は仮のものです。実際の実装では従業員情報を
        参照するデータベースやファイルからデータを取得する必要があります。
        """
        # TODO: 実際のデータソースからメールアドレスを取得する実装
        return None
    
    def _get_emails_from_df(self, df: pd.DataFrame) -> List[str]:
        """
        DataFrameからメールアドレスのリストを取得
        
        Note: この実装は仮のものです。実際の実装ではDataFrame内の
        適切な列からメールアドレスを抽出する必要があります。
        """
        # TODO: 実際のDataFrameからメールアドレスを抽出する実装
        return []

# 使用例
if __name__ == "__main__":
    config = DeliverFlagConfig(
        application_path="申請書.xlsx",
        leave_files={
            "産休": "産休.xlsx",
            "休職": "休職者.xlsx"
        },
        current_deliver_flag_path="current_deliver_flag.xlsx",
        output_path="deliver_flag.xlsx"
    )
    
    processor = DeliverFlagProcessor(config)
    processor.process()