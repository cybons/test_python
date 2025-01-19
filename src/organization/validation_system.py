# validation_system.py

"""
WEVOXシステムのバリデーション機能を提供するモジュール
複数階層でのバリデーションチェックを実装し、エラーハンドリングを行います。
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class ValidationError:
    """バリデーションエラーを表現するデータクラス"""

    error_type: str
    message: str
    details: Optional[dict] = None


class BaseValidator(ABC):
    """バリデータの基底クラス"""

    def __init__(self):
        self.errors: list[ValidationError] = []

    @abstractmethod
    def validate(self) -> bool:
        """バリデーションを実行する抽象メソッド"""
        pass

    def add_error(
        self, error_type: str, message: str, details: Optional[dict] = None
    ) -> None:
        """エラーを追加するヘルパーメソッド"""
        self.errors.append(ValidationError(error_type, message, details))


class FileExistenceValidator(BaseValidator):
    """必要なファイルの存在チェックを行うバリデータ"""

    def __init__(self, folder_path: str, required_files: list[str]):
        super().__init__()
        self.folder_path = folder_path
        self.required_files = required_files

    def validate(self) -> bool:
        """必要なファイルが存在するかチェック"""
        existing_files = set(os.listdir(self.folder_path))
        missing_files = []

        for required_file in self.required_files:
            if required_file not in existing_files:
                missing_files.append(required_file)
                self.add_error(
                    "file_missing",
                    f"必要なファイル {required_file} が見つかりません",
                    {"file": required_file},
                )

        return len(missing_files) == 0


class ManualFileFormatValidator(BaseValidator):
    """手動作成ファイルのフォーマットをチェックするバリデータ"""

    def __init__(self, file_path: str, expected_columns: list[str]):
        super().__init__()
        self.file_path = file_path
        self.expected_columns = expected_columns
        self.df: Optional[pd.DataFrame] = None

    def validate(self) -> bool:
        """ファイルフォーマットの検証を実行"""
        try:
            self.df = (
                pd.read_excel(self.file_path)
                if self.file_path.endswith(".xlsx")
                else pd.read_csv(self.file_path)
            )

            # 必須カラムの存在チェック
            missing_columns = set(self.expected_columns) - set(self.df.columns)
            if missing_columns:
                self.add_error(
                    "missing_columns",
                    f"必須カラムが不足しています: {', '.join(missing_columns)}",
                    {"missing_columns": list(missing_columns)},
                )
                return False

            # データ型チェック
            invalid_formats = self._check_data_formats()
            if invalid_formats:
                return False

            return True

        except Exception as e:
            self.add_error(
                "file_read_error",
                f"ファイルの読み込みに失敗しました: {str(e)}",
                {"error": str(e)},
            )
            return False

    def _check_data_formats(self) -> bool:
        """各カラムのデータ型をチェック"""
        is_valid = True

        # データ型チェックのロジックをここに実装
        # 例: 数値であるべき列に文字列が含まれていないかなど

        return is_valid


class SystemDataCompatibilityValidator(BaseValidator):
    """システムデータとの互換性をチェックするバリデータ"""

    def __init__(
        self, manual_data: pd.DataFrame, system_data: pd.DataFrame, key_column: str
    ):
        super().__init__()
        self.manual_data = manual_data
        self.system_data = system_data
        self.key_column = key_column

    def validate(self) -> bool:
        """システムデータとの互換性を検証"""
        # キー列の存在チェック
        if (
            self.key_column not in self.manual_data.columns
            or self.key_column not in self.system_data.columns
        ):
            self.add_error(
                "key_column_missing",
                f"キー列 {self.key_column} が見つかりません",
                {"key_column": self.key_column},
            )
            return False

        # キー値の整合性チェック
        manual_keys = set(self.manual_data[self.key_column])
        system_keys = set(self.system_data[self.key_column])

        invalid_keys = manual_keys - system_keys
        if invalid_keys:
            self.add_error(
                "invalid_keys",
                f"システムに存在しないキーが含まれています: {', '.join(map(str, invalid_keys))}",
                {"invalid_keys": list(invalid_keys)},
            )
            return False

        return True


class ValidationOrchestrator:
    """バリデーション全体を統括するオーケストレーター"""

    def __init__(self):
        self.validators: list[BaseValidator] = []
        self.all_errors: list[ValidationError] = []

    def add_validator(self, validator: BaseValidator) -> None:
        """バリデータを追加"""
        self.validators.append(validator)

    def validate_all(self) -> bool:
        """全てのバリデーションを実行"""
        is_valid = True
        self.all_errors = []

        for validator in self.validators:
            if not validator.validate():
                is_valid = False
                self.all_errors.extend(validator.errors)

        return is_valid

    def get_error_summary(self) -> dict:
        """エラーサマリーを生成"""
        return {
            "total_errors": len(self.all_errors),
            "errors_by_type": self._group_errors_by_type(),
            "all_errors": [
                {"type": err.error_type, "message": err.message, "details": err.details}
                for err in self.all_errors
            ],
        }

    def _group_errors_by_type(self) -> dict:
        """エラーを種類ごとにグループ化"""
        error_groups = {}
        for error in self.all_errors:
            if error.error_type not in error_groups:
                error_groups[error.error_type] = []
            error_groups[error.error_type].append(error.message)
        return error_groups


# 使用例
def main():
    # ファイル存在チェック
    file_validator = FileExistenceValidator(
        "data/", ["user.csv", "org.csv", "manual_input.xlsx"]
    )

    # 手動ファイルフォーマットチェック
    format_validator = ManualFileFormatValidator(
        "data/manual_input.xlsx", ["user_id", "org_code", "status"]
    )

    # システムデータ互換性チェック
    compatibility_validator = SystemDataCompatibilityValidator(
        manual_data=pd.DataFrame(),  # 実際のデータを設定
        system_data=pd.DataFrame(),  # 実際のデータを設定
        key_column="user_id",
    )

    # バリデーションの実行
    orchestrator = ValidationOrchestrator()
    orchestrator.add_validator(file_validator)
    orchestrator.add_validator(format_validator)
    orchestrator.add_validator(compatibility_validator)

    is_valid = orchestrator.validate_all()
    if not is_valid:
        error_summary = orchestrator.get_error_summary()
        print("バリデーションエラー:")
        print(error_summary)


if __name__ == "__main__":
    main()
