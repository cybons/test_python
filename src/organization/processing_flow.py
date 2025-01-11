from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

@dataclass
class UserOrgMapping:
    """ユーザーと組織の紐付け情報"""
    user_id: str
    org_code: str
    source: str  # データソース（'individual_sheet' or 'system'）
    priority: int  # 優先順位（個別シート：1、システム：2など）

class DataProcessor:
    """データ処理の中核クラス"""
    
    def __init__(self):
        self.user_org_mappings: Dict[str, UserOrgMapping] = {}  # user_id をキーとする
        self.org_tree = {}  # 組織ツリー情報
        
    def load_system_data(self, system_df: pd.DataFrame):
        """システムデータの読み込み（基本マッピング）"""
        for _, row in system_df.iterrows():
            user_id = row['user_id']
            if user_id not in self.user_org_mappings:
                self.user_org_mappings[user_id] = UserOrgMapping(
                    user_id=user_id,
                    org_code=row['org_code'],
                    source='system',
                    priority=2
                )
    
    def load_individual_sheet(self, individual_df: pd.DataFrame):
        """個別登録シートの読み込み（優先マッピング）"""
        for _, row in individual_df.iterrows():
            user_id = row['user_id']
            self.user_org_mappings[user_id] = UserOrgMapping(
                user_id=user_id,
                org_code=row['org_code'],
                source='individual_sheet',
                priority=1
            )

class AdminMembersGenerator:
    """admin_members.xlsx生成クラス"""
    
    def __init__(self, data_processor: DataProcessor):
        self.data_processor = data_processor
        
    def generate(self) -> pd.DataFrame:
        """admin_members.xlsx用のDataFrame生成"""
        records = []
        
        for mapping in self.data_processor.user_org_mappings.values():
            org_info = self.data_processor.org_tree.get(mapping.org_code, {})
            
            record = {
                'ユーザーID': mapping.user_id,
                '組織コード': mapping.org_code,
                '組織名': org_info.get('name', ''),
                '組織フルパス': org_info.get('full_path', ''),
                'データソース': mapping.source,
                # その他必要な情報
            }
            records.append(record)
            
        return pd.DataFrame(records)

class ProcessManager:
    """処理全体の制御クラス"""
    
    def __init__(self):
        self.data_processor = DataProcessor()
        self.admin_generator = AdminMembersGenerator(self.data_processor)
        
    def process(self):
        """メイン処理フロー"""
        # 1. システムデータの読み込み
        system_df = self.load_system_data()
        self.data_processor.load_system_data(system_df)
        
        # 2. 個別シートの読み込み
        individual_df = self.load_individual_sheet()
        self.data_processor.load_individual_sheet(individual_df)
        
        # 3. 組織ツリーの構築
        self.build_org_tree()
        
        # 4. admin_members.xlsx の生成
        admin_df = self.admin_generator.generate()
        
        # 5. ファイル出力
        self.export_to_excel(admin_df, 'admin_members.xlsx')

# 使用例
def main():
    manager = ProcessManager()
    manager.process()