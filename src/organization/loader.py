# loaders/base_loader.py
"""
各種ファイルローダーの基底クラスを提供するモジュール
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

import pandas as pd


class BaseLoader(ABC):
    """ファイルローダーの基底クラス"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._validate_file_existence()

    def _validate_file_existence(self) -> None:
        """ファイルの存在確認"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

    @abstractmethod
    def load(self) -> Any:
        """ファイルを読み込む抽象メソッド"""
        pass


# loaders/excel_loader.py
"""
Excelファイルのロードを行うモジュール
"""
from pathlib import Path
from typing import Optional, Dict

import pandas as pd

from .base_loader import BaseLoader


class ExcelLoader(BaseLoader):
    """Excelファイルを読み込むクラス"""

    def __init__(
        self,
        file_path: Path,
        sheet_names: Optional[list[str]] = None,
        header_row: int = 0,
    ):
        """
        Args:
            file_path: Excelファイルのパス
            sheet_names: 読み込むシート名のリスト。Noneの場合は全シート
            header_row: ヘッダー行の位置
        """
        super().__init__(file_path)
        self.sheet_names = sheet_names
        self.header_row = header_row

    def load(self) -> Dict[str, pd.DataFrame]:
        """
        Excelファイルを読み込む

        Returns:
            Dict[str, pd.DataFrame]: シート名をキーとするDataFrameの辞書
        """
        return pd.read_excel(
            self.file_path,
            sheet_name=self.sheet_names,
            header=self.header_row
        )


# loaders/csv_loader.py
"""
CSVファイルのロードを行うモジュール
"""
from pathlib import Path
import pandas as pd

from .base_loader import BaseLoader


class CSVLoader(BaseLoader):
    """CSVファイルを読み込むクラス"""

    def __init__(
        self,
        file_path: Path,
        encoding: str = "utf-8",
        delimiter: str = ",",
    ):
        """
        Args:
            file_path: CSVファイルのパス
            encoding: ファイルのエンコーディング
            delimiter: 区切り文字
        """
        super().__init__(file_path)
        self.encoding = encoding
        self.delimiter = delimiter

    def load(self) -> pd.DataFrame:
        """
        CSVファイルを読み込む

        Returns:
            pd.DataFrame: 読み込んだデータ
        """
        return pd.read_csv(
            self.file_path,
            encoding=self.encoding,
            delimiter=self.delimiter
        )


# preprocessors/base_preprocessor.py
"""
前処理の基底クラスを提供するモジュール
"""
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BasePreprocessor(ABC):
    """前処理の基底クラス"""

    @abstractmethod
    def preprocess(self, data: Any) -> pd.DataFrame:
        """
        データの前処理を行う抽象メソッド

        Args:
            data: 前処理を行うデータ

        Returns:
            pd.DataFrame: 前処理済みのデータ
        """
        pass


# preprocessors/application_preprocessor.py
"""
申請書データの前処理を行うモジュール
"""
from typing import Dict

import pandas as pd

from .base_preprocessor import BasePreprocessor


class ApplicationPreprocessor(BasePreprocessor):
    """申請書データの前処理クラス"""

    def __init__(self, column_mappings: Dict[str, str]):
        """
        Args:
            column_mappings: カラム名のマッピング辞書
        """
        self.column_mappings = column_mappings

    def preprocess(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        申請書データの前処理を実行

        Args:
            data: シート名をキーとするDataFrameの辞書

        Returns:
            Dict[str, pd.DataFrame]: 前処理済みのDataFrame辞書
        """
        processed_data = {}
        for sheet_name, df in data.items():
            processed_df = df.copy()
            
            # カラム名の変更
            if sheet_name in self.column_mappings:
                processed_df = processed_df.rename(
                    columns=self.column_mappings[sheet_name]
                )
            
            # 空行の削除
            processed_df = processed_df.dropna(how="all")
            
            # データ型の変換
            processed_df = self._convert_data_types(processed_df)
            
            processed_data[sheet_name] = processed_df
            
        return processed_data

    def _convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        データ型の変換処理

        Args:
            df: 変換対象のDataFrame

        Returns:
            pd.DataFrame: データ型変換後のDataFrame
        """
        # 必要に応じてデータ型の変換処理を実装
        return df


# preprocessors/system_preprocessor.py
"""
システムデータの前処理を行うモジュール
"""
import pandas as pd

from .base_preprocessor import BasePreprocessor


class SystemPreprocessor(BasePreprocessor):
    """システムデータの前処理クラス"""

    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        システムデータの前処理を実行

        Args:
            data: 前処理対象のDataFrame

        Returns:
            pd.DataFrame: 前処理済みのDataFrame
        """
        processed_df = data.copy()
        
        # 空白の削除
        processed_df = processed_df.apply(
            lambda x: x.str.strip() if x.dtype == "object" else x
        )
        
        # 重複行の削除
        processed_df = processed_df.drop_duplicates()
        
        return processed_df
        
        
        
 # loaders/base.py
"""
ファイルローダーの基底クラスを提供するモジュール
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

import pandas as pd

# 戻り値の型を表すジェネリック型
T = TypeVar('T')

@dataclass
class LoaderResult(Generic[T]):
    """ローダーの結果を表すデータクラス"""
    data: T
    warnings: list[str]
    metadata: dict[str, Any]

class BaseFileLoader(ABC):
    """ファイルローダーの基底クラス"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.warnings: list[str] = []

    def _validate_file_existence(self) -> None:
        """ファイルの存在確認"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

    @abstractmethod
    def load(self) -> LoaderResult:
        """
        ファイルを読み込む抽象メソッド

        Returns:
            LoaderResult: 読み込み結果、警告、メタデータを含む
        """
        pass

    def _add_warning(self, message: str) -> None:
        """警告メッセージを追加"""
        self.warnings.append(message)


# loaders/generic.py
"""
汎用ローダーの実装
"""
from pathlib import Path
from typing import Dict, Optional, Union

import pandas as pd

from .base import BaseFileLoader, LoaderResult


class GenericExcelLoader(BaseFileLoader):
    """汎用Excelローダー"""

    def __init__(
        self,
        file_path: Path,
        sheet_names: Optional[Union[str, list[str]]] = None
    ):
        super().__init__(file_path)
        self.sheet_names = sheet_names

    def load(self) -> LoaderResult[Dict[str, pd.DataFrame]]:
        """Excelファイルを読み込む"""
        self._validate_file_existence()

        try:
            excel_file = pd.ExcelFile(self.file_path)
            
            # シート名の検証
            if self.sheet_names:
                missing_sheets = set(self.sheet_names) - set(excel_file.sheet_names)
                if missing_sheets:
                    self._add_warning(f"Missing sheets: {missing_sheets}")

            # データの読み込み
            data = pd.read_excel(
                excel_file,
                sheet_name=self.sheet_names
            )

            # メタデータの収集
            metadata = {
                "file_path": str(self.file_path),
                "sheet_names": excel_file.sheet_names,
                "file_size": self.file_path.stat().st_size
            }

            return LoaderResult(
                data=data,
                warnings=self.warnings,
                metadata=metadata
            )

        except Exception as e:
            raise RuntimeError(f"Failed to load Excel file: {e}")


# loaders/wevox_specific.py
"""
WEVOX専用ローダーの実装
"""
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Dict, List

import pandas as pd

from .base import BaseFileLoader, LoaderResult


@dataclass
class ApplicationFormConfig:
    """申請書の設定"""
    delivery_sheet: str = "配信組織"
    skip_rows: int = 22
    required_sheets: List[str] = None
    column_types: Dict[str, str] = None

    def __post_init__(self):
        if self.required_sheets is None:
            self.required_sheets = ["配信組織", "個別設定"]
        if self.column_types is None:
            self.column_types = {
                "組織コード": "str",
                "配下含む": "bool"
            }


class ApplicationFormLoader(BaseFileLoader):
    """申請書専用ローダー"""

    # クラス定数
    DEFAULT_SETTINGS: ClassVar[dict] = {
        "date_columns": ["適用開始日", "適用終了日"],
        "required_columns": ["組織コード", "配下含む"]
    }

    def __init__(self, file_path: Path, config: Optional[ApplicationFormConfig] = None):
        super().__init__(file_path)
        self.config = config or ApplicationFormConfig()

    def load(self) -> LoaderResult[Dict[str, pd.DataFrame]]:
        """申請書を読み込む"""
        self._validate_file_existence()

        try:
            excel_file = pd.ExcelFile(self.file_path)
            
            # 必須シートの存在確認
            self._validate_required_sheets(excel_file)

            # データの読み込みと前処理
            data = {}
            
            # 配信組織シートの読み込み
            delivery_df = self._load_delivery_sheet(excel_file)
            if not delivery_df.empty:
                data["delivery"] = delivery_df

            # 個別設定シートの読み込み
            individual_dfs = self._load_individual_sheets(excel_file)
            if individual_dfs:
                data["individual"] = pd.concat(individual_dfs, ignore_index=True)

            # メタデータの収集
            metadata = {
                "file_path": str(self.file_path),
                "sheet_names": excel_file.sheet_names,
                "config": self.config.__dict__,
                "row_counts": {
                    sheet: df.shape[0] for sheet, df in data.items()
                }
            }

            return LoaderResult(
                data=data,
                warnings=self.warnings,
                metadata=metadata
            )

        except Exception as e:
            raise RuntimeError(f"Failed to load application form: {e}")

    def _validate_required_sheets(self, excel_file: pd.ExcelFile) -> None:
        """必須シートの存在確認"""
        missing_sheets = set(self.config.required_sheets) - set(excel_file.sheet_names)
        if missing_sheets:
            raise ValueError(f"Required sheets not found: {missing_sheets}")

    def _load_delivery_sheet(self, excel_file: pd.ExcelFile) -> pd.DataFrame:
        """配信組織シートの読み込み"""
        df = pd.read_excel(
            excel_file,
            sheet_name=self.config.delivery_sheet,
            skiprows=self.config.skip_rows
        )

        # カラムの存在確認
        missing_columns = set(self.DEFAULT_SETTINGS["required_columns"]) - set(df.columns)
        if missing_columns:
            self._add_warning(f"Missing columns in delivery sheet: {missing_columns}")

        # データ型の変換
        for col, dtype in self.config.column_types.items():
            if col in df.columns:
                try:
                    df[col] = df[col].astype(dtype)
                except Exception as e:
                    self._add_warning(f"Failed to convert column {col} to {dtype}: {e}")

        return df

    def _load_individual_sheets(self, excel_file: pd.ExcelFile) -> List[pd.DataFrame]:
        """個別設定シートの読み込み"""
        individual_dfs = []
        for sheet_name in excel_file.sheet_names:
            if sheet_name != self.config.delivery_sheet:
                try:
                    df = pd.read_excel(
                        excel_file,
                        sheet_name=sheet_name,
                        skiprows=self.config.skip_rows
                    )
                    if not df.empty:
                        df["source_sheet"] = sheet_name
                        individual_dfs.append(df)
                except Exception as e:
                    self._add_warning(f"Error loading sheet {sheet_name}: {e}")
        return individual_dfs


# 使用例
def example_usage():
    # 1. 汎用Excelローダーの使用
    generic_loader = GenericExcelLoader(
        Path("simple_export.xlsx"),
        sheet_names=["Sheet1", "Sheet2"]
    )
    generic_result = generic_loader.load()
    
    if generic_result.warnings:
        print("Warnings:", generic_result.warnings)
    
    # 2. 申請書専用ローダーの使用
    config = ApplicationFormConfig(
        delivery_sheet="配信組織",
        skip_rows=22,
        required_sheets=["配信組織", "個別設定A", "個別設定B"],
        column_types={
            "組織コード": "str",
            "配下含む": "bool",
            "適用開始日": "datetime64[ns]"
        }
    )
    
    app_loader = ApplicationFormLoader(
        Path("申請書.xlsx"),
        config=config
    )
    app_result = app_loader.load()
    
    # 警告の確認
    if app_result.warnings:
        print("Application form warnings:", app_result.warnings)
    
    # メタデータの確認
    print("Metadata:", app_result.metadata)

if __name__ == "__main__":
    example_usage()