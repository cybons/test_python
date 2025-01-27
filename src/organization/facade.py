"""
WEVOXシステムの各種処理を統合的に管理するファサードモジュール。
各プロセッサの連携と実行フローを管理します。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from .csv_processor import CSVProcessor
from .data_processor import DataProcessor
from .sys_import import AdminUsersProcessor
from .user_data_preprocessor import UserDataPreprocessor, UserDataMergeConfig
from .deliver_flg import DeliverFlagConfig, DeliverFlagProcessor
from .exclusion_processor import ExclusionProcessor


@dataclass
class WevoxProcessConfig:
    """WEVOXシステム処理の設定を保持するデータクラス"""
    
    input_dir: Path
    output_dir: Path
    system_csv_dir: Path
    config_path: Path
    exclusion_files: dict[str, Path]
    delivery_config: DeliverFlagConfig


class WevoxProcessFacade:
    """
    WEVOXシステムの処理フローを管理するファサードクラス
    
    このクラスは以下の処理を統合的に管理します：
    1. システムCSVの読み込みと前処理
    2. ユーザーデータの処理
    3. 除外対象者の処理
    4. 配信フラグの設定
    """
    
    def __init__(self, config: WevoxProcessConfig):
        """
        Parameters:
            config: WEVOXシステム処理の設定
        """
        self.config = config
        self.csv_processor = None
        self.processed_user_data = None
        self.admin_users = None
        self.excluded_users = None
        self.deliver_flags = None

    def process(self) -> None:
        """
        一連の処理を実行します
        
        処理の流れ：
        1. CSVデータの読み込みと前処理
        2. ユーザーデータの処理
        3. Admin Usersの生成
        4. 除外対象者の処理
        5. 配信フラグの設定
        6. 結果の出力
        """
        try:
            # 1. CSVデータの読み込みと前処理
            self._initialize_csv_processor()
            
            # 2. ユーザーデータの処理
            self._process_user_data()
            
            # 3. Admin Usersの生成
            self._generate_admin_users()
            
            # 4. 除外対象者の処理
            self._process_exclusions()
            
            # 5. 配信フラグの設定
            self._set_delivery_flags()
            
            # 6. 結果の出力
            self._export_results()
            
        except Exception as e:
            raise RuntimeError(f"処理中にエラーが発生しました: {str(e)}") from e

    def _initialize_csv_processor(self) -> None:
        """CSVプロセッサの初期化と前処理"""
        self.csv_processor = CSVProcessor(
            folder_path=str(self.config.system_csv_dir),
            config_path=str(self.config.config_path)
        )

    def _process_user_data(self) -> None:
        """ユーザーデータの処理"""
        # デフォルトのマージ設定を使用
        merge_config = UserDataMergeConfig()
        
        # ユーザーデータの前処理を実行
        preprocessor = UserDataPreprocessor(
            csv_processor=self.csv_processor,
            merge_config=merge_config
        )
        
        self.processed_user_data = preprocessor.preprocess_user_data()

    def _generate_admin_users(self) -> None:
        """Admin Usersの生成"""
        processor = AdminUsersProcessor()
        
        # システムデータの読み込み
        data_files = {
            'user': self.config.system_csv_dir / 'user.csv',
            'userapp': self.config.system_csv_dir / 'userapp.csv',
            'location': self.config.system_csv_dir / 'location.csv',
            'user_org_title': self.config.system_csv_dir / 'user_org_title.csv',
            'org': self.config.system_csv_dir / 'org.csv',
            'title': self.config.system_csv_dir / 'title.csv'
        }
        
        processor.load_data(data_files)
        self.admin_users = processor.process_admin_users()

    def _process_exclusions(self) -> None:
        """除外対象者の処理"""
        processor = ExclusionProcessor(self.processed_user_data)
        
        # 除外ファイルの処理
        for category, file_path in self.config.exclusion_files.items():
            if file_path.exists():
                exclusion_df = pd.read_excel(file_path)
                processor.add_exclusion_data(category, exclusion_df)
        
        processor.process_exclusions()
        self.excluded_users = processor.get_all_excluded_users()

    def _set_delivery_flags(self) -> None:
        """配信フラグの設定"""
        processor = DeliverFlagProcessor(self.config.delivery_config)
        processor.process()
        self.deliver_flags = processor.processed_users

    def _export_results(self) -> None:
        """処理結果の出力"""
        # Admin Usersの出力
        admin_users_path = self.config.output_dir / 'admin_members.xlsx'
        self.admin_users.to_excel(admin_users_path, index=False)
        
        # 除外対象者リストの出力
        exclusion_path = self.config.output_dir / 'excluded_users.xlsx'
        with pd.ExcelWriter(exclusion_path) as writer:
            pd.DataFrame({'user_id': self.excluded_users}).to_excel(
                writer, 
                sheet_name='除外対象者',
                index=False
            )
        
        # 配信フラグの出力
        deliver_flag_path = self.config.output_dir / 'deliver_flag.xlsx'
        self.deliver_flags.to_excel(deliver_flag_path, index=False)


# 使用例
def main():
    # 設定の作成
    config = WevoxProcessConfig(
        input_dir=Path('input'),
        output_dir=Path('output'),
        system_csv_dir=Path('input/system'),
        config_path=Path('config/column_config.xlsx'),
        exclusion_files={
            'maternity': Path('input/産休.xlsx'),
            'childcare': Path('input/育休.xlsx'),
            'leave': Path('input/休職.xlsx')
        },
        delivery_config=DeliverFlagConfig(
            application_path='input/申請書.xlsx',
            leave_files={
                '産休': 'input/産休.xlsx',
                '休職': 'input/休職者.xlsx'
            },
            output_path='output/deliver_flag.xlsx'
        )
    )
    
    # ファサードを使用した処理の実行
    facade = WevoxProcessFacade(config)
    facade.process()


if __name__ == "__main__":
    main()
