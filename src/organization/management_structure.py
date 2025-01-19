from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set

import pandas as pd


@dataclass
class UserAssignment:
    """ユーザーの組織割り当て情報を保持するデータクラス"""

    user_id: str
    org_codes: Set[str]  # ユーザーに割り当てられた組織コード
    operation: str  # "add" (追加), "replace" (置換), "remove" (削除)
    source_sheet: str  # データの出所となるシート名


@dataclass
class DeliveryCondition:
    """配信条件を保持するデータクラス"""

    org_code: str
    include_sub_orgs: bool
    employment_types: list[str]
    exclusion_users: set[str]  # 除外対象ユーザー


class DeliverySheetManager:
    """配信組織シートの管理を行うクラス"""

    def __init__(self, delivery_sheet_df: pd.DataFrame):
        self.delivery_df = delivery_sheet_df
        self.conditions: dict[str, DeliveryCondition] = {}
        self._process_delivery_sheet()

    def _process_delivery_sheet(self):
        """配信シートを処理し、条件をパース"""
        for _, row in self.delivery_df.iterrows():
            condition = DeliveryCondition(
                org_code=row["組織コード"],
                include_sub_orgs=row["配下含む"] == 1,
                employment_types=self._parse_employment_types(row["雇用形態"]),
                exclusion_users=set(),  # 初期状態では空
            )
            self.conditions[row["組織コード"]] = condition

    def _parse_employment_types(self, emp_types_str: str) -> list[str]:
        """雇用形態文字列をパース"""
        return [et.strip() for et in emp_types_str.split(",") if et.strip()]

    def get_target_orgs(self) -> Set[str]:
        """配信対象となる組織コードの一覧を取得"""
        return set(self.conditions.keys())


class IndividualSheetManager:
    """個別登録シートの管理を行うクラス"""

    def __init__(self):
        self.assignments: list[UserAssignment] = []
        self._processed_sheets: Set[str] = set()

    def process_sheet(self, sheet_df: pd.DataFrame, sheet_name: str):
        """個別登録シートを処理"""
        if sheet_name in self._processed_sheets:
            return

        for _, row in sheet_df.iterrows():
            assignment = UserAssignment(
                user_id=row["ユーザーID"],
                org_codes=set(str(row["組織コード"]).split(",")),
                operation=row["操作"],  # "add", "replace", "remove"
                source_sheet=sheet_name,
            )
            self.assignments.append(assignment)

        self._processed_sheets.add(sheet_name)

    def get_user_assignments(self, user_id: str) -> list[UserAssignment]:
        """特定ユーザーの割り当て情報を取得"""
        return [a for a in self.assignments if a.user_id == user_id]


class ApplicationFormManager:
    """申請ファイル全体の管理を行うクラス"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.delivery_manager: Optional[DeliverySheetManager] = None
        self.individual_manager = IndividualSheetManager()

    def process_file(self):
        """申請ファイルの処理を実行"""
        excel = pd.ExcelFile(self.file_path)

        # 配信組織シートの処理
        delivery_df = pd.read_excel(excel, sheet_name="配信組織")
        self.delivery_manager = DeliverySheetManager(delivery_df)

        # 個別登録シートの処理
        for sheet_name in excel.sheet_names:
            if sheet_name != "配信組織":
                individual_df = pd.read_excel(excel, sheet_name=sheet_name)
                self.individual_manager.process_sheet(individual_df, sheet_name)

    def get_final_assignments(self) -> dict[str, Set[str]]:
        """最終的なユーザーの組織割り当てを計算"""
        if not self.delivery_manager:
            raise ValueError("File must be processed first")

        final_assignments: dict[str, Set[str]] = {}
        base_orgs = self.delivery_manager.get_target_orgs()

        # ベースとなる配信組織の割り当て
        for org_code in base_orgs:
            condition = self.delivery_manager.conditions[org_code]
            # ここで組織とユーザーの紐付けロジックを実装
            # （実際の実装では、雇用形態なども考慮する必要があります）

        # 個別登録による上書き
        for assignment in self.individual_manager.assignments:
            if assignment.operation == "add":
                if assignment.user_id not in final_assignments:
                    final_assignments[assignment.user_id] = set()
                final_assignments[assignment.user_id].update(assignment.org_codes)
            elif assignment.operation == "replace":
                final_assignments[assignment.user_id] = assignment.org_codes
            elif assignment.operation == "remove":
                if assignment.user_id in final_assignments:
                    final_assignments[assignment.user_id].difference_update(
                        assignment.org_codes
                    )

        return final_assignments

    def validate_assignments(self) -> list[str]:
        """割り当ての整合性チェック"""
        errors = []
        final_assignments = self.get_final_assignments()

        for user_id, orgs in final_assignments.items():
            # 組織が空になっていないかチェック
            if not orgs:
                errors.append(f"User {user_id} has no organization assignments")

            # その他の検証ルール...

        return errors


# 使用例
def process_application_form(file_path: str):
    manager = ApplicationFormManager(Path(file_path))
    manager.process_file()

    # 最終的な割り当てを取得
    assignments = manager.get_final_assignments()

    # 整合性チェック
    errors = manager.validate_assignments()

    return assignments, errors
