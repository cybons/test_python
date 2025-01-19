# main.py - メイン処理フロー
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class WevoxConfig:
    """WEVOX システムの設定"""

    input_dir: Path
    output_dir: Path
    log_dir: Path
    system_export_files: dict[str, Path]
    application_files: dict[str, Path]
    wevox_export_files: dict[str, Path]


class WevoxProcessor:
    """WEVOX システムのメイン処理クラス"""

    def __init__(self, config: WevoxConfig):
        self.config = config
        self.setup_logging()

    def setup_logging(self):
        """ログ設定"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(self.config.log_dir / "wevox.log"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def process_month_start(self):
        """月初処理"""
        try:
            # 1. 申請書の読み込みと検証
            applications = self.load_applications()

            # 2. システムデータの読み込み
            system_data = self.load_system_data()

            # 3. WEVOXエクスポートデータの読み込み
            wevox_data = self.load_wevox_data()

            # 4. データの更新処理
            processor = DataUpdateProcessor(system_data, applications, wevox_data)
            updated_data = processor.process()

            # 5. 出力ファイルの生成
            self.generate_output_files(updated_data)

            self.logger.info("月初処理が完了しました")

        except Exception as e:
            self.logger.error(f"月初処理でエラーが発生しました: {str(e)}")
            raise

    def process_month_end(self):
        """月末処理"""
        try:
            # 1. 退職者・休職者データの読み込み
            employee_status = self.load_employee_status()

            # 2. システムデータの更新
            processor = MonthEndProcessor(employee_status)
            updated_data = processor.process()

            # 3. 出力ファイルの生成
            self.generate_month_end_files(updated_data)

            self.logger.info("月末処理が完了しました")

        except Exception as e:
            self.logger.error(f"月末処理でエラーが発生しました: {str(e)}")
            raise


# interfaces.py - データ入出力インターフェース


class DataLoader:
    """データ読み込みの基底クラス"""

    def load_csv(self, file_path: Path) -> pd.DataFrame:
        """CSVファイルの読み込み"""
        try:
            return pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding="cp932")

    def load_excel(
        self, file_path: Path, sheet_name: Optional[str] = None
    ) -> pd.DataFrame:
        """Excelファイルの読み込み"""
        return pd.read_excel(file_path, sheet_name=sheet_name)


class SystemDataLoader(DataLoader):
    """システムエクスポートデータの読み込み"""

    def load_all(self, file_paths: Dict[str, Path]) -> Dict[str, pd.DataFrame]:
        """全システムデータの読み込み"""
        return {name: self.load_csv(path) for name, path in file_paths.items()}


class ApplicationLoader(DataLoader):
    """申請書データの読み込み"""

    def load_all(self, file_paths: Dict[str, Path]) -> Dict[str, pd.DataFrame]:
        """全申請書の読み込み"""
        return {name: self.load_excel(path) for name, path in file_paths.items()}


# processors.py - データ処理クラス


class DataUpdateProcessor:
    """データ更新処理クラス"""

    def __init__(
        self,
        system_data: Dict[str, pd.DataFrame],
        applications: Dict[str, pd.DataFrame],
        wevox_data: Dict[str, pd.DataFrame],
    ):
        self.system_data = system_data
        self.applications = applications
        self.wevox_data = wevox_data

    def process(self) -> Dict[str, pd.DataFrame]:
        """データ更新の実行"""
        # 1. ユーザー情報の更新
        users = self.update_users()

        # 2. グループ情報の更新
        groups = self.update_groups()

        # 3. 配信対象の選定
        delivery_targets = self.select_delivery_targets()

        return {"users": users, "groups": groups, "delivery_targets": delivery_targets}

    def update_users(self) -> pd.DataFrame:
        """ユーザー情報の更新"""
        # Admin/Engagementユーザーの区分け
        # ユーザー情報の更新処理
        pass

    def update_groups(self) -> pd.DataFrame:
        """グループ情報の更新"""
        # グループの新規作成/リネーム処理
        # 組織変更の反映
        pass

    def select_delivery_targets(self) -> pd.DataFrame:
        """配信対象の選定"""
        # 配信対象条件の適用
        # 除外対象の処理
        pass


# 使用例
if __name__ == "__main__":
    config = WevoxConfig(
        input_dir=Path("input"),
        output_dir=Path("output"),
        log_dir=Path("logs"),
        system_export_files={
            "users": Path("input/user.csv"),
            "org": Path("input/org.csv"),
            # ... 他のファイル
        },
        application_files={
            "delivery": Path("input/配信申請書.xlsx"),
            "access": Path("input/閲覧権限申請書.xlsx"),
            # ... 他の申請書
        },
        wevox_export_files={
            "deliver_flag": Path("input/deliver_flg.xlsx"),
            "members": Path("input/メンバー.xlsx"),
            # ... 他のエクスポートファイル
        },
    )

    processor = WevoxProcessor(config)

    # 月初処理の実行
    processor.process_month_start()

    # 月末処理の実行
    processor.process_month_end()
