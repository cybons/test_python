from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path
import pandas as pd

@dataclass
class ValidationError:
    error_type: str
    message: str
    sheet_name: Optional[str] = None
    column_name: Optional[str] = None

class BaseValidator(ABC):
    @abstractmethod
    def validate(self) -> List[ValidationError]:
        pass

class FileExistenceValidator(BaseValidator):
    def __init__(self, file_path: Path, required_sheets: List[str]):
        self.file_path = file_path
        self.required_sheets = required_sheets
        
    def validate(self) -> List[ValidationError]:
        errors = []
        if not self.file_path.exists():
            errors.append(
                ValidationError(
                    error_type="FILE_NOT_FOUND",
                    message=f"Required file not found: {self.file_path}"
                )
            )
            return errors
            
        try:
            excel = pd.ExcelFile(self.file_path)
            missing_sheets = set(self.required_sheets) - set(excel.sheet_names)
            if missing_sheets:
                errors.append(
                    ValidationError(
                        error_type="MISSING_SHEETS",
                        message=f"Missing required sheets: {', '.join(missing_sheets)}"
                    )
                )
        except Exception as e:
            errors.append(
                ValidationError(
                    error_type="FILE_READ_ERROR",
                    message=f"Failed to read Excel file: {str(e)}"
                )
            )
            
        return errors

class HeaderValidator(BaseValidator):
    def __init__(self, file_path: Path, sheet_headers: Dict[str, List[str]]):
        self.file_path = file_path
        self.sheet_headers = sheet_headers
        
    def validate(self) -> List[ValidationError]:
        errors = []
        try:
            excel = pd.ExcelFile(self.file_path)
            for sheet_name, required_headers in self.sheet_headers.items():
                if sheet_name not in excel.sheet_names:
                    continue
                    
                df = pd.read_excel(excel, sheet_name=sheet_name)
                missing_headers = set(required_headers) - set(df.columns)
                
                if missing_headers:
                    errors.append(
                        ValidationError(
                            error_type="MISSING_HEADERS",
                            message=f"Missing required headers: {', '.join(missing_headers)}",
                            sheet_name=sheet_name
                        )
                    )
        except Exception as e:
            errors.append(
                ValidationError(
                    error_type="HEADER_VALIDATION_ERROR",
                    message=f"Failed to validate headers: {str(e)}"
                )
            )
        
        return errors

class ContentValidator(BaseValidator):
    def __init__(self, file_path: Path, master_data: Dict[str, pd.DataFrame], validation_rules: Dict[str, Dict]):
        self.file_path = file_path
        self.master_data = master_data
        self.validation_rules = validation_rules
        
    def validate(self) -> List[ValidationError]:
        errors = []
        try:
            excel = pd.ExcelFile(self.file_path)
            for sheet_name, rules in self.validation_rules.items():
                if sheet_name not in excel.sheet_names:
                    continue
                    
                df = pd.read_excel(excel, sheet_name=sheet_name)
                
                # マスターデータとの整合性チェック
                for column, master_info in rules.get('master_validation', {}).items():
                    if column not in df.columns:
                        continue
                        
                    master_df = self.master_data.get(master_info['master_name'])
                    if master_df is None:
                        continue
                        
                    invalid_values = set(df[column]) - set(master_df[master_info['master_column']])
                    if invalid_values:
                        errors.append(
                            ValidationError(
                                error_type="INVALID_MASTER_DATA",
                                message=f"Values not found in master data: {', '.join(map(str, invalid_values))}",
                                sheet_name=sheet_name,
                                column_name=column
                            )
                        )
                
                # その他のバリデーションルール
                # 必要に応じて追加
                
        except Exception as e:
            errors.append(
                ValidationError(
                    error_type="CONTENT_VALIDATION_ERROR",
                    message=f"Failed to validate content: {str(e)}"
                )
            )
            
        return errors

class ApplicationFormValidator:
    def __init__(self, file_path: Path, required_sheets: List[str], 
                 sheet_headers: Dict[str, List[str]], 
                 master_data: Dict[str, pd.DataFrame],
                 validation_rules: Dict[str, Dict]):
        self.file_existence_validator = FileExistenceValidator(file_path, required_sheets)
        self.header_validator = HeaderValidator(file_path, sheet_headers)
        self.content_validator = ContentValidator(file_path, master_data, validation_rules)
        
    def validate(self) -> List[ValidationError]:
        # ファイル存在チェック
        existence_errors = self.file_existence_validator.validate()
        if existence_errors:
            return existence_errors
            
        # ヘッダーチェック
        header_errors = self.header_validator.validate()
        if header_errors:
            return header_errors
            
        # コンテンツチェック
        content_errors = self.content_validator.validate()
        return content_errors

# 使用例
def validate_application_form(file_path: str):
    required_sheets = ['配信申請', '閲覧権限']
    sheet_headers = {
        '配信申請': ['組織コード', '配下含むフラグ', '雇用形態'],
        '閲覧権限': ['ユーザーID', 'アクセス権限']
    }
    master_data = {
        'organizations': pd.DataFrame({'org_code': ['001', '002', '003']}),
        'employment_types': pd.DataFrame({'type_code': ['1', '2', '3']})
    }
    validation_rules = {
        '配信申請': {
            'master_validation': {
                '組織コード': {'master_name': 'organizations', 'master_column': 'org_code'},
                '雇用形態': {'master_name': 'employment_types', 'master_column': 'type_code'}
            }
        }
    }
    
    validator = ApplicationFormValidator(
        Path(file_path),
        required_sheets,
        sheet_headers,
        master_data,
        validation_rules
    )
    
    errors = validator.validate()
    return errors