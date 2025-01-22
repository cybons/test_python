from typing import Dict, List, Set, Tuple
import pandas as pd
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime

@dataclass
class RenameOperation:
    """名称変更操作を表すデータクラス"""
    group_code: str  # 新設組織の場合は空文字列
    old_name: str
    new_name: str
    is_temp: bool = False
    is_new: bool = False  # 新設組織フラグ

class OrganizationRenameSimulator:
    def __init__(self, org_data: pd.DataFrame):
        """
        組織名称変更のシミュレーションを行うクラス
        
        Parameters:
        - org_data: 組織データ (group_code, prev_month_fullname, current_month_fullnameを含む)
        """
        self.org_data = org_data
        self.temp_suffix = "_TEMP_RENAME"
        # 末梢組織のカウンター初期化
        self.discontinued_counter = defaultdict(int)

    def _validate_org_names(self) -> None:
        """組織名の形式と重複を検証"""
        # 1. 形式の検証
        current_orgs = self.org_data[
            self.org_data['current_month_fullname'].notna()
        ]['current_month_fullname']
        
        invalid_current = [
            name for name in current_orgs 
            if not name.startswith('部署/')
        ]
        
        if invalid_current:
            raise ValueError(
                f"Invalid organization names found (must start with '部署/'): {invalid_current}"
            )

        # 2. 当月内での組織名重複チェック
        current_month_names = self.org_data['current_month_fullname'].dropna()
        current_duplicates = current_month_names[current_month_names.duplicated()].unique()
        if len(current_duplicates) > 0:
            raise ValueError(
                f"Duplicate organization names found in current month: {current_duplicates}"
            )

        # 3. 前月内での組織名重複チェック
        prev_month_names = self.org_data['prev_month_fullname'].dropna()
        prev_duplicates = prev_month_names[prev_month_names.duplicated()].unique()
        if len(prev_duplicates) > 0:
            raise ValueError(
                f"Duplicate organization names found in previous month: {prev_duplicates}"
            )

        # 4. 新設組織の重複チェック
        new_orgs = self.org_data[
            (self.org_data['prev_month_fullname'].isna()) & 
            (self.org_data['current_month_fullname'].notna())
        ]['current_month_fullname']

        existing_names = set(self.org_data['prev_month_fullname'].dropna())
        duplicates_with_existing = set(new_orgs) & existing_names
        if duplicates_with_existing:
            raise ValueError(
                f"New organization names conflict with existing organizations: {duplicates_with_existing}"
            )

    def _get_discontinued_name(self, org_name: str) -> str:
        """末梢組織名を生成"""
        today = datetime.now().strftime('%Y/%m/%d')
        self.discontinued_counter[today] += 1
        counter = str(self.discontinued_counter[today]).zfill(2)
        return f"末梢組織/{org_name}（{today}_{counter}）"

    def _process_discontinued_orgs(self, processed_names: Set[str]) -> List[RenameOperation]:
        """末梢組織の処理"""
        operations = []
        discontinued_orgs = self.org_data[
            (self.org_data['prev_month_fullname'].notna()) & 
            (self.org_data['current_month_fullname'].isna())
        ]
        
        for _, row in discontinued_orgs.iterrows():
            discontinued_name = self._get_discontinued_name(row['prev_month_fullname'])
            operations.append(
                RenameOperation(
                    row['group_code'],
                    row['prev_month_fullname'],
                    discontinued_name,
                    is_temp=False
                )
            )
            processed_names.add(row['prev_month_fullname'])
            
        return operations

    def _process_direct_renames(
        self, rename_orgs: pd.DataFrame, prev_month_names: Set[str], 
        processed_names: Set[str]
    ) -> List[RenameOperation]:
        """変更後の名称が前月組織に存在しない変更を処理"""
        operations = []
        
        for _, row in rename_orgs.iterrows():
            if (row['current_month_fullname'] not in prev_month_names and 
                row['prev_month_fullname'] not in processed_names):
                operations.append(
                    RenameOperation(
                        row['group_code'],
                        row['prev_month_fullname'],
                        row['current_month_fullname'],
                        is_temp=False
                    )
                )
                processed_names.add(row['prev_month_fullname'])
                
        return operations

    def _process_complex_renames(
        self, rename_orgs: pd.DataFrame, prev_month_names: Set[str], 
        processed_names: Set[str]
    ) -> Tuple[List[RenameOperation], List[RenameOperation]]:
        """変更後の名称が前月組織に存在する変更を処理"""
        temp_operations = []
        final_operations = []
        
        for _, row in rename_orgs.iterrows():
            if row['prev_month_fullname'] not in processed_names:
                if row['current_month_fullname'] in prev_month_names:
                    # テンポラリ名称への変更
                    temp_name = f"{row['prev_month_fullname']}{self.temp_suffix}"
                    temp_operations.append(
                        RenameOperation(
                            row['group_code'],
                            row['prev_month_fullname'],
                            temp_name,
                            is_temp=True
                        )
                    )
                    # 最終名称への変更
                    final_operations.append(
                        RenameOperation(
                            row['group_code'],
                            temp_name,
                            row['current_month_fullname'],
                            is_temp=False
                        )
                    )
                else:
                    # 直接の名称変更
                    final_operations.append(
                        RenameOperation(
                            row['group_code'],
                            row['prev_month_fullname'],
                            row['current_month_fullname'],
                            is_temp=False
                        )
                    )
                processed_names.add(row['prev_month_fullname'])
                
        return temp_operations, final_operations

    def _process_new_orgs(self) -> List[RenameOperation]:
        """新設組織の処理"""
        operations = []
        new_orgs = self.org_data[
            (self.org_data['prev_month_fullname'].isna()) & 
            (self.org_data['current_month_fullname'].notna())
        ]
        
        for _, row in new_orgs.iterrows():
            operations.append(
                RenameOperation(
                    '',  # 空のgroup_code
                    '',  # 新設のため old_name は空
                    row['current_month_fullname'],
                    is_temp=False,
                    is_new=True
                )
            )
            
        return operations

    def generate_rename_operations(self) -> Tuple[List[RenameOperation], List[RenameOperation]]:
        """
        名称変更操作のリストを生成
        
        Returns:
        - Tuple[List[RenameOperation], List[RenameOperation]]: 
          (一時名称への変更操作リスト, 最終名称への変更操作リスト)
        """
        self._validate_org_names()
        
        temp_operations = []
        final_operations = []
        processed_names = set()  # 既に処理済みの組織名を追跡
        
        # 前月の組織名セット
        prev_month_names = set(self.org_data['prev_month_fullname'].dropna())
        
        # 名称変更が必要な組織を抽出
        rename_orgs = self.org_data[
            (self.org_data['prev_month_fullname'].notna()) & 
            (self.org_data['current_month_fullname'].notna()) &
            (self.org_data['prev_month_fullname'] != self.org_data['current_month_fullname'])
        ]
        
        # 1. 末梢組織の処理
        final_operations.extend(self._process_discontinued_orgs(processed_names))
        
        # 2. 直接の名称変更を処理
        final_operations.extend(
            self._process_direct_renames(rename_orgs, prev_month_names, processed_names)
        )
        
        # 3. 複雑な名称変更を処理
        temp_ops, final_ops = self._process_complex_renames(
            rename_orgs, prev_month_names, processed_names
        )
        temp_operations.extend(temp_ops)
        final_operations.extend(final_ops)
        
        # 4. 新設組織の処理
        final_operations.extend(self._process_new_orgs())
        
        return temp_operations, final_operations

    def generate_excel_files(self, first_import_path: str, second_import_path: str) -> None:
        """
        名称変更操作をExcelファイルとして出力
        2段階のインポート用に2つのファイルを生成します
        
        Parameters:
        - first_import_path: 1回目のインポート用Excelファイルのパス（テンポラリ名称変更と末梢組織）
        - second_import_path: 2回目のインポート用Excelファイルのパス（最終名称変更と新設組織）
        """
        temp_ops, final_ops = self.generate_rename_operations()
        
        # 1回目のインポート用データ準備
        first_import_data = []
        
        # テンポラリ名称への変更
        for op in temp_ops:
            first_import_data.append({
                'group_code': op.group_code,
                'current_name': op.old_name,
                'new_name': op.new_name
            })
            
        # 末梢組織の処理
        discontinued_ops = [
            op for op in final_ops 
            if op.new_name.startswith('末梢組織/')
        ]
        for op in discontinued_ops:
            first_import_data.append({
                'group_code': op.group_code,
                'current_name': op.old_name,
                'new_name': op.new_name
            })
            
        # 2回目のインポート用データ準備
        rename_ops = []  # 名称変更
        new_orgs = []    # 新設組織
        
        for op in final_ops:
            if op.is_new:
                new_orgs.append({
                    'group_code': '',
                    'org_name': op.new_name
                })
            elif not op.new_name.startswith('末梢組織/'):  # 末梢組織以外の名称変更
                if op.old_name.endswith(self.temp_suffix):
                    # テンポラリ名称からの変更
                    rename_ops.append({
                        'group_code': op.group_code,
                        'current_name': op.old_name,
                        'new_name': op.new_name
                    })
                elif not any(t.new_name == op.old_name for t in temp_ops):
                    # 直接の名称変更（テンポラリを経由しないもの）
                    rename_ops.append({
                        'group_code': op.group_code,
                        'current_name': op.old_name,
                        'new_name': op.new_name
                    })
        
        # 1回目のインポートファイル
        if first_import_data:
            with pd.ExcelWriter(first_import_path) as writer:
                pd.DataFrame(first_import_data).to_excel(
                    writer,
                    index=False,
                    sheet_name='First Import'
                )
        
        # 2回目のインポートファイル
        with pd.ExcelWriter(second_import_path) as writer:
            if rename_ops:
                pd.DataFrame(rename_ops).to_excel(
                    writer,
                    index=False,
                    sheet_name='Rename Operations'
                )
            if new_orgs:
                pd.DataFrame(new_orgs).to_excel(
                    writer,
                    index=False,
                    sheet_name='New Organizations'
                )