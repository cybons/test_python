# data_processing.py

"""
WEVOXシステムのデータ処理とバリデーションを統合的に管理するモジュール。
データの読み込み、前処理、バリデーションを段階的に実行します。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass
class ProcessingResult:
    """データ処理の結果を表すデータクラス"""

    success: bool
    message: str
    data: Optional[pd.DataFrame] = None
    errors: Optional[list[str]] = None


class DataProcessor:
    """データの読み込みと前処理を管理するクラス"""

    def __init__(self, config: dict):
        """
        初期化

        Args:
            config (dict): 設定情報
                - required_system_files: システムファイルの設定
                - required_manual_files: 手動作成ファイルの設定
                - column_mappings: カラムのマッピング情報
        """
        self.config = config
        self.system_data: dict[str, pd.DataFrame] = {}
        self.manual_data: dict[str, pd.DataFrame] = {}
        self.processed_data: dict[str, pd.DataFrame] = {}

    def process(self) -> ProcessingResult:
        """
        データ処理のメインフロー

        Returns:
            ProcessingResult: 処理結果
        """
        try:
            # 1. システムファイルの存在チェックと読み込み
            system_files_result = self._load_system_files()
            if not system_files_result.success:
                return system_files_result

            # 2. システムデータの前処理
            preprocess_result = self._preprocess_system_data()
            if not preprocess_result.success:
                return preprocess_result

            # 3. 手動ファイルの存在チェックと読み込み
            manual_files_result = self._load_manual_files()
            if not manual_files_result.success:
                return manual_files_result

            # 4. 手動ファイルのバリデーション
            validation_result = self._validate_manual_files()
            if not validation_result.success:
                return validation_result

            # 5. システムデータとの整合性チェック
            compatibility_result = self._check_system_compatibility()
            if not compatibility_result.success:
                return compatibility_result

            # 6. 最終的なデータ処理
            final_result = self._process_final_data()
            return final_result

        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"処理中にエラーが発生しました: {str(e)}",
                errors=[str(e)],
            )

    def _load_system_files(self) -> ProcessingResult:
        """システムファイルの読み込み"""
        required_files = self.config["required_system_files"]
        missing_files = []

        for file_config in required_files:
            file_path = Path(file_config["path"])
            if not file_path.exists():
                missing_files.append(str(file_path))
                continue

            try:
                df = pd.read_csv(file_path, encoding="utf-8")
                self.system_data[file_config["name"]] = df
            except Exception as e:
                return ProcessingResult(
                    success=False,
                    message=f"システムファイル {file_path} の読み込みに失敗: {str(e)}",
                    errors=[str(e)],
                )

        if missing_files:
            return ProcessingResult(
                success=False,
                message="必要なシステムファイルが見つかりません",
                errors=[f"Missing files: {', '.join(missing_files)}"],
            )

        return ProcessingResult(
            success=True, message="システムファイルの読み込みが完了しました"
        )

    def _preprocess_system_data(self) -> ProcessingResult:
        """システムデータの前処理"""
        try:
            # カラム名の標準化
            for name, df in self.system_data.items():
                if name in self.config["column_mappings"]:
                    df.rename(
                        columns=self.config["column_mappings"][name], inplace=True
                    )

            # 必要な前処理（データ型変換、欠損値処理など）
            # ... 前処理のロジック ...

            return ProcessingResult(
                success=True, message="システムデータの前処理が完了しました"
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                message="システムデータの前処理に失敗しました",
                errors=[str(e)],
            )

    def _load_manual_files(self) -> ProcessingResult:
        """手動作成ファイルの読み込み"""
        required_files = self.config["required_manual_files"]
        missing_files = []

        for file_config in required_files:
            file_path = Path(file_config["path"])
            if not file_path.exists():
                missing_files.append(str(file_path))
                continue

            try:
                if file_path.suffix == ".xlsx":
                    df = pd.read_excel(file_path)
                else:
                    df = pd.read_csv(file_path, encoding="utf-8")
                self.manual_data[file_config["name"]] = df
            except Exception as e:
                return ProcessingResult(
                    success=False,
                    message=f"手動ファイル {file_path} の読み込みに失敗: {str(e)}",
                    errors=[str(e)],
                )

        if missing_files:
            return ProcessingResult(
                success=False,
                message="必要な手動ファイルが見つかりません",
                errors=[f"Missing files: {', '.join(missing_files)}"],
            )

        return ProcessingResult(
            success=True, message="手動ファイルの読み込みが完了しました"
        )

    def _validate_manual_files(self) -> ProcessingResult:
        """手動ファイルのバリデーション"""
        all_errors = []

        for name, df in self.manual_data.items():
            if name not in self.config["manual_file_validations"]:
                continue

            validation_rules = self.config["manual_file_validations"][name]

            # 必須カラムチェック
            missing_columns = set(validation_rules["required_columns"]) - set(
                df.columns
            )
            if missing_columns:
                all_errors.append(
                    f"ファイル {name} に必要なカラムがありません: {missing_columns}"
                )

            # データ型チェック
            for column, expected_type in validation_rules.get(
                "column_types", {}
            ).items():
                if column not in df.columns:
                    continue

                if expected_type == "numeric":
                    non_numeric = df[~df[column].str.match(r"^\d*\.?\d*$")]
                    if not non_numeric.empty:
                        all_errors.append(
                            f"ファイル {name} の {column} に数値以外のデータが含まれています"
                        )

                # 他のデータ型チェックもここに追加

        if all_errors:
            return ProcessingResult(
                success=False,
                message="手動ファイルのバリデーションでエラーが検出されました",
                errors=all_errors,
            )

        return ProcessingResult(
            success=True, message="手動ファイルのバリデーションが完了しました"
        )

    def _check_system_compatibility(self) -> ProcessingResult:
        """システムデータとの整合性チェック"""
        all_errors = []

        for name, manual_df in self.manual_data.items():
            if name not in self.config["compatibility_checks"]:
                continue

            check_config = self.config["compatibility_checks"][name]
            system_df = self.system_data.get(check_config["system_file"])

            if system_df is None:
                all_errors.append(
                    f"システムファイル {check_config['system_file']} が見つかりません"
                )
                continue

            # キー列の存在チェック
            key_column = check_config["key_column"]
            if (
                key_column not in manual_df.columns
                or key_column not in system_df.columns
            ):
                all_errors.append(f"キー列 {key_column} が見つかりません")
                continue

            # 参照整合性チェック
            manual_keys = set(manual_df[key_column])
            system_keys = set(system_df[key_column])
            invalid_keys = manual_keys - system_keys

            if invalid_keys:
                all_errors.append(
                    f"システムに存在しないキーが検出されました: {invalid_keys}"
                )

        if all_errors:
            return ProcessingResult(
                success=False,
                message="システムデータとの整合性チェックでエラーが検出されました",
                errors=all_errors,
            )

        return ProcessingResult(
            success=True, message="システムデータとの整合性チェックが完了しました"
        )

    def _process_final_data(self) -> ProcessingResult:
        """最終的なデータ処理"""
        try:
            # 最終的なデータ処理ロジック
            # ... 処理ロジック ...

            return ProcessingResult(
                success=True,
                message="データ処理が完了しました",
                data=pd.DataFrame(),  # 実際の処理結果のDataFrame
            )

        except Exception as e:
            return ProcessingResult(
                success=False, message="最終データ処理に失敗しました", errors=[str(e)]
            )


# 使用例
def main():
    # 設定情報
    config = {
        "required_system_files": [
            {"name": "users", "path": "data/system/users.csv"},
            {"name": "organizations", "path": "data/system/organizations.csv"},
        ],
        "required_manual_files": [
            {"name": "manual_input", "path": "data/manual/input.xlsx"}
        ],
        "column_mappings": {
            "users": {"user_id": "id", "user_name": "name"},
            "organizations": {"org_id": "id", "org_name": "name"},
        },
        "manual_file_validations": {
            "manual_input": {
                "required_columns": ["user_id", "org_code", "status"],
                "column_types": {"user_id": "numeric", "status": "string"},
            }
        },
        "compatibility_checks": {
            "manual_input": {"system_file": "users", "key_column": "user_id"}
        },
    }

    # データ処理の実行
    processor = DataProcessor(config)
    result = processor.process()

    if result.success:
        print("処理成功:", result.message)
        if result.data is not None:
            print("処理結果:", result.data.head())
    else:
        print("処理失敗:", result.message)
        if result.errors:
            print("エラー詳細:")
            for error in result.errors:
                print(f"- {error}")


if __name__ == "__main__":
    main()
