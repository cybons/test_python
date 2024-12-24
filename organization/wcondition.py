import pandas as pd

class Filter:
    def __init__(self, ord_df: pd.DataFrame, user_df: pd.DataFrame, condition_df: pd.DataFrame, rank_code_columns: list):
        self.ord_df = ord_df
        self.user_df = user_df
        self.condition_df = condition_df
        self.rank_code_columns = rank_code_columns
        self.combined_org_mask = pd.Series(False, index=ord_df.index)
        self.combined_user_mask = pd.Series(False, index=user_df.index)
    
    def _get_employment_mask(self, condition: pd.Series) -> pd.Series:
        """Create an employment mask based on the condition."""
        employment_conditions = {
            '正社員': condition.get('正社員含む', False),
            '派遣社員': condition.get('派遣社員含む', False),
            '契約社員': condition.get('契約社員含む', False)
        }
        # Filter only the employment types to include
        active_employments = [etype for etype, include in employment_conditions.items() if include]
        if not active_employments:
            return pd.Series(False, index=self.user_df.index)
        return self.user_df['雇用形態区分'].isin(active_employments)
    
    def _apply_org_condition(self, org_code: str, include_sub: bool) -> pd.Series:
        """Create an organization mask based on the org_code and include_sub flag."""
        if include_sub:
            # Check if any of the rank_code_columns match the org_code
            sub_org_mask = self.ord_df[self.rank_code_columns].eq(org_code).any(axis=1)
        else:
            sub_org_mask = self.ord_df['組織コード'] == org_code
        return sub_org_mask
    
    def apply_conditions(self):
        """Apply all conditions to update the combined masks."""
        for _, condition in self.condition_df.iterrows():
            org_code = condition['組織コード']
            include_sub = condition['配下含む']
            
            # Update organization mask
            org_mask = self._apply_org_condition(org_code, include_sub)
            self.combined_org_mask |= org_mask
            
            # Get relevant organization codes after applying the current org_mask
            relevant_org_codes = self.ord_df.loc[org_mask, '組織コード']
            
            # Update user mask based on relevant organizations and employment types
            relevant_users = self.user_df['組織コード'].isin(relevant_org_codes)
            employment_mask = self._get_employment_mask(condition)
            self.combined_user_mask |= (relevant_users & employment_mask)
    
    def filter_data(self):
        """Filter the organization and user data based on combined masks."""
        self.apply_conditions()
        
        # Filter organization DataFrame
        target_org_df = self.ord_df[self.combined_org_mask].copy()
        non_target_org_df = self.ord_df[~self.combined_org_mask].copy()
        
        # Filter user DataFrame
        target_user_df = self.user_df[self.combined_user_mask].copy()
        non_target_user_df = self.user_df[~self.combined_user_mask].copy()
        
        return target_org_df, non_target_org_df, target_user_df, non_target_user_df

# Usage Example
if __name__ == "__main__":
    # Assuming ord_df, user_df, condition_df, and rank_code_columns are predefined DataFrames and list
    filter = Filter(ord_df, user_df, condition_df, rank_code_columns)
    target_org_df, non_target_org_df, target_user_df, non_target_user_df = filter.filter_data()
    
    print("対象組織（クラス使用）:")
    print(target_org_df)
    print("\n対象外組織（クラス使用）:")
    print(non_target_org_df)
    print("\n対象ユーザー（クラス使用）:")
    print(target_user_df)
    print("\n対象外ユーザー（クラス使用）:")
    print(non_target_user_df)