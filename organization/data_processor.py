import pandas as pd
from typing import Literal

class DataProcessor:
    """データ処理の中核クラス"""
    
    def __init__(self):
        # 基本となるユーザー・組織のマッピング
        self.user_org_df: pd.DataFrame = pd.DataFrame()
        # 組織のフルパス情報
        self.org_tree_df: pd.DataFrame = pd.DataFrame()
    
    def load_system_data(self, system_df: pd.DataFrame):
        """
        システムデータからの基本データ読み込み
        
        Parameters
        ----------
        system_df : pd.DataFrame
            columns = ['user_id', 'org_name', 'org_fullpath', ...]
        """
        # 基本となるユーザー・組織マッピングを作成
        self.user_org_df = system_df[['user_id', 'org_name']].copy()
        self.user_org_df['source'] = 'system'
        self.user_org_df['priority'] = 2
        
        # 組織ツリー情報を構築
        self.org_tree_df = (
            system_df[['org_name', 'org_fullpath']]
            .drop_duplicates()
            .copy()
        )
    
    def update_from_individual_sheet(self, individual_df: pd.DataFrame):
        """
        個別申請シートからの更新
        
        Parameters
        ----------
        individual_df : pd.DataFrame
            columns = ['user_id', 'org_name', 'update_type', ...]
            update_type: Literal['update', 'add']
        """
        # 更新タイプごとに処理
        update_mask = individual_df['update_type'] == 'update'
        add_mask = individual_df['update_type'] == 'add'
        
        # 更新処理（既存のマッピングを置換）
        if update_mask.any():
            update_data = individual_df[update_mask]
            
            # 更新対象のユーザーを一旦削除
            self.user_org_df = self.user_org_df[
                ~self.user_org_df['user_id'].isin(update_data['user_id'])
            ]
            
            # 新しいマッピングを追加
            update_records = pd.DataFrame({
                'user_id': update_data['user_id'],
                'org_name': update_data['org_name'],
                'source': 'individual',
                'priority': 1
            })
            self.user_org_df = pd.concat([self.user_org_df, update_records], ignore_index=True)
        
        # 追加処理（既存組織に追加のマッピング）
        if add_mask.any():
            add_data = individual_df[add_mask]
            add_records = pd.DataFrame({
                'user_id': add_data['user_id'],
                'org_name': add_data['org_name'],
                'source': 'individual',
                'priority': 1
            })
            self.user_org_df = pd.concat([self.user_org_df, add_records], ignore_index=True)
        
        # 仮想組織の追加
        virtual_orgs = (
            individual_df[['org_name', 'org_fullpath']]
            .drop_duplicates()
            .copy()
        )
        # 既存の組織ツリーにない組織を追加
        new_orgs = virtual_orgs[~virtual_orgs['org_name'].isin(self.org_tree_df['org_name'])]
        if not new_orgs.empty:
            self.org_tree_df = pd.concat([self.org_tree_df, new_orgs], ignore_index=True)
    
    def get_final_mapping(self) -> pd.DataFrame:
        """
        最終的なマッピング結果を取得
        
        Returns
        -------
        pd.DataFrame
            WEVOX用の組織フルパスを含む最終マッピング
        """
        return pd.merge(
            self.user_org_df,
            self.org_tree_df,
            on='org_name',
            how='left'
        )