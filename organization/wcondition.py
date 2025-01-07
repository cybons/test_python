from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd

@dataclass
class FilterConfig:
    """フィルタリング設定を保持するデータクラス
    
    Attributes:
        org_code_column: 組織コードの列名
        emp_type_column: 雇用形態区分の列名
        valid_emp_types: 有効な雇用形態の種類
        rank_code_columns: ランクコードの列名リスト
    """
    org_code_column: str = "組織コード"
    emp_type_column: str = "雇用形態区分"
    valid_emp_types: List[str] = ("正社員", "派遣社員", "契約社員")
    rank_code_columns: List[str] = None

@dataclass
class FilterResult:
    """フィルタリング結果を保持するデータクラス"""
    target_org_df: pd.DataFrame
    non_target_org_df: pd.DataFrame
    target_user_df: pd.DataFrame
    non_target_user_df: pd.DataFrame

class Filter:
    """組織とユーザーデータのフィルタリングを行うクラス
    
    このクラスは組織データとユーザーデータに対して、
    条件に基づいたフィルタリングを適用します。
    """

    def __init__(
        self,
        ord_df: pd.DataFrame,
        user_df: pd.DataFrame,
        condition_df: pd.DataFrame,
        config: Optional[FilterConfig] = None
    ):
        """
        Args:
            ord_df: 組織データを含むDataFrame
            user_df: ユーザーデータを含むDataFrame
            condition_df: フィルタリング条件を含むDataFrame
            config: フィルタリング設定。Noneの場合はデフォルト設定を使用
        
        Raises:
            ValueError: 必要な列が存在しない場合
        """
        self._validate_dataframes(ord_df, user_df, condition_df)
        self.ord_df = ord_df
        self.user_df = user_df
        self.condition_df = condition_df
        self.config = config or FilterConfig()
        
        # マスクの初期化
        self.combined_org_mask = pd.Series(False, index=ord_df.index)
        self.combined_user_mask = pd.Series(False, index=user_df.index)

    def _validate_dataframes(
        self,
        ord_df: pd.DataFrame,
        user_df: pd.DataFrame,
        condition_df: pd.DataFrame
    ) -> None:
        """入力DataFrameのバリデーションを行う
        
        Args:
            ord_df: 組織データを含むDataFrame
            user_df: ユーザーデータを含むDataFrame
            condition_df: フィルタリング条件を含むDataFrame
            
        Raises:
            ValueError: 必要な列が存在しない場合
        """
        required_ord_columns = {self.config.org_code_column}
        required_user_columns = {
            self.config.org_code_column,
            self.config.emp_type_column
        }
        required_condition_columns = {"組織コード", "配下含む"}

        if not required_ord_columns.issubset(ord_df.columns):
            raise ValueError(f"組織DataFrameに必要な列が存在しません: {required_ord_columns}")
        if not required_user_columns.issubset(user_df.columns):
            raise ValueError(f"ユーザーDataFrameに必要な列が存在しません: {required_user_columns}")
        if not required_condition_columns.issubset(condition_df.columns):
            raise ValueError(f"条件DataFrameに必要な列が存在しません: {required_condition_columns}")

    def _get_employment_mask(self, condition: pd.Series) -> pd.Series:
        """雇用形態に基づくマスクを作成
        
        Args:
            condition: フィルタリング条件を含むSeries
            
        Returns:
            pd.Series: 条件に合致する雇用形態のマスク
        """
        employment_conditions = {
            emp_type: condition.get(f'{emp_type}含む', False)
            for emp_type in self.config.valid_emp_types
        }
        
        active_employments = [
            etype for etype, include in employment_conditions.items()
            if include
        ]
        
        if not active_employments:
            return pd.Series(False, index=self.user_df.index)
            
        return self.user_df[self.config.emp_type_column].isin(active_employments)

    def _apply_org_condition(
        self,
        org_code: str,
        include_sub: bool
    ) -> pd.Series:
        """組織コードと配下フラグに基づくマスクを作成
        
        Args:
            org_code: 組織コード
            include_sub: 配下組織を含むかどうか
            
        Returns:
            pd.Series: 条件に合致する組織のマスク
        """
        try:
            if include_sub and self.config.rank_code_columns:
                return self.ord_df[self.config.rank_code_columns].eq(org_code).any(axis=1)
            return self.ord_df[self.config.org_code_column] == org_code
        except KeyError as e:
            raise ValueError(f"指定された列が存在しません: {e}")

    def apply_conditions(self) -> None:
        """全ての条件を適用してマスクを更新"""
        for _, condition in self.condition_df.iterrows():
            try:
                org_code = condition['組織コード']
                include_sub = condition['配下含む']
                
                # 組織マスクの更新
                org_mask = self._apply_org_condition(org_code, include_sub)
                self.combined_org_mask |= org_mask
                
                # 関連する組織コードの取得
                relevant_org_codes = self.ord_df.loc[
                    org_mask,
                    self.config.org_code_column
                ]
                
                # ユーザーマスクの更新
                relevant_users = self.user_df[self.config.org_code_column].isin(
                    relevant_org_codes
                )
                employment_mask = self._get_employment_mask(condition)
                self.combined_user_mask |= (relevant_users & employment_mask)
                
            except Exception as e:
                logging.error(f"条件の適用中にエラーが発生: {str(e)}")
                raise

    def filter_data(self) -> FilterResult:
        """データのフィルタリングを実行
        
        Returns:
            FilterResult: フィルタリング結果を含むデータクラス
            
        Raises:
            ValueError: フィルタリング処理中にエラーが発生した場合
        """
        try:
            self.apply_conditions()
            
            return FilterResult(
                target_org_df=self.ord_df[self.combined_org_mask].copy(),
                non_target_org_df=self.ord_df[~self.combined_org_mask].copy(),
                target_user_df=self.user_df[self.combined_user_mask].copy(),
                non_target_user_df=self.user_df[~self.combined_user_mask].copy()
            )
            
        except Exception as e:
            logging.error(f"フィルタリング処理中にエラーが発生: {str(e)}")
            raise ValueError(f"フィルタリング処理に失敗しました: {str(e)}")