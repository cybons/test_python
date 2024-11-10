from logging import getLogger

import pandas as pd
from exceptions.custom_exceptions import ColumnRenameError
from utils import handle_errors

logger = getLogger(__name__)


class UserProcessor:
    def __init__(self, df: pd.DataFrame, config, dataframe_name: str):
        self.df = df
        self.config = config
        self.dataframe_name = dataframe_name
        self.excluded_dfs = {}

    def _handle_error(self, error: Exception):
        """エラー処理を一元化するメソッド"""
        logger.error(f"Error in {self.dataframe_name}: {str(error)}")
        raise error  # 必要に応じてエラーを再スロー

    @handle_errors
    def rename_columns(self):
        rename_mapping = self.config.get_rename_mapping(self.dataframe_name)
        if rename_mapping:
            missing_columns = [
                col for col in rename_mapping.keys() if col not in self.df.columns
            ]
            if missing_columns:
                raise ColumnRenameError(missing_columns, self.dataframe_name)
            logger.info(f"Renaming columns for {self.dataframe_name}")
            self.df = self.df.rename(columns=rename_mapping)
        return self

    @handle_errors
    def filter_exclusions(self):
        exclusions = self.config.get("exclusions")
        mask = pd.Series([True] * len(self.df))
        for key, values in exclusions.items():
            if key in self.df.columns:
                exclusion_mask = self.df[key].isin(values)
                self.excluded_dfs[key] = self.df[exclusion_mask].copy()
                mask &= ~exclusion_mask
        self.df = self.df[mask].copy()
        logger.info(f"Filtered exclusions for {self.dataframe_name}")
        return self

    @handle_errors
    def merge_additional_info(self, additional_dfs: dict, on_key: str):
        for key, additional_df in additional_dfs.items():
            logger.info(f"Merging {key} information into {self.dataframe_name}")
            self.df = self.df.merge(
                additional_df, on=on_key, how="left", suffixes=("", f"_{key}")
            )
        return self

    @handle_errors
    def label_age(self):
        age_bins = self.config.get("age_bins")
        age_labels = self.config.get("age_labels")
        if "age" in self.df.columns and age_bins and age_labels:
            logger.info(f"Labeling age groups for {self.dataframe_name}")
            self.df["age_group"] = pd.cut(
                self.df["age"], bins=age_bins, labels=age_labels
            )
        else:
            logger.warning(
                f"Age column or bins/labels not found for {self.dataframe_name}"
            )
        return self

    @handle_errors
    def label_employment_type(self):
        if "is_dispatch" in self.df.columns and "is_new_employee" in self.df.columns:
            logger.info(f"Labeling employment types for {self.dataframe_name}")
            self.df["employment_type"] = "Regular"
            self.df.loc[self.df["is_dispatch"] is True, "employment_type"] = "Dispatch"
            self.df.loc[self.df["is_new_employee"] is True, "employment_type"] = (
                "New Employee"
            )
        else:
            logger.warning(
                f"Employment type columns not found for {self.dataframe_name}"
            )
        return self

    def get_processed_df(self) -> pd.DataFrame:
        return self.df

    def get_excluded_dfs(self) -> dict:
        return self.excluded_dfs

    def __enter__(self):
        # 初期化処理や前処理
        logger.info(f"Starting processing for {self.dataframe_name}")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # 後処理やクリーンアップ
        if exc_type:
            logger.error(f"An error occurred: {exc_value}")
        logger.info(f"Finished processing for {self.dataframe_name}")
