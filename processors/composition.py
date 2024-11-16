import logging
from abc import ABC, abstractmethod

import pandas as pd

# ログの基本設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# カスタム例外クラス
class InitializationError(Exception):
    pass


class InitializationManager:
    """初期化と状態管理を担当するクラス"""

    def __init__(self, df: pd.DataFrame = None):
        self.df = df.copy() if df is not None else None
        self.is_initialized = df is not None

    def ensure_initialized(self):
        if not self.is_initialized:
            raise InitializationError(
                "データが初期化されていません。先に初期化を行ってください。"
            )

    def initialize(self, df: pd.DataFrame):
        self.df = df.copy()
        self.is_initialized = True
        logging.info("InitializationManager: データの初期化が完了しました。")


class BaseProcessor(ABC):
    """プロセッサの基底クラス"""

    def __init__(self, init_manager: InitializationManager):
        self.init_manager = init_manager

    @abstractmethod
    def preprocess(self):
        pass


class ProcessorA(BaseProcessor):
    def preprocess(self):
        self.init_manager.ensure_initialized()
        df = self.init_manager.df
        try:
            df.rename(columns={"old_name_A1": "new_name_A1"}, inplace=True)
            df.drop(columns=["unnecessary_column_A"], inplace=True)
            logging.info("ProcessorA: 前処理が完了しました。")
        except KeyError as e:
            logging.error(f"ProcessorA: 前処理中にエラーが発生しました。{e}")
            raise


class ProcessorB(BaseProcessor):
    def preprocess(self):
        self.init_manager.ensure_initialized()
        df = self.init_manager.df
        try:
            df.rename(columns={"old_name_B1": "new_name_B1"}, inplace=True)
            df.drop(columns=["unnecessary_column_B"], inplace=True)
            logging.info("ProcessorB: 前処理が完了しました。")
        except KeyError as e:
            logging.error(f"ProcessorB: 前処理中にエラーが発生しました。{e}")
            raise


class ProcessorC(BaseProcessor):
    def preprocess(self):
        self.init_manager.ensure_initialized()
        df = self.init_manager.df
        try:
            df.rename(columns={"old_name_C1": "new_name_C1"}, inplace=True)
            df.drop(columns=["unnecessary_column_C"], inplace=True)
            logging.info("ProcessorC: 前処理が完了しました。")
        except KeyError as e:
            logging.error(f"ProcessorC: 前処理中にエラーが発生しました。{e}")
            raise


class ProcessorD(BaseProcessor):
    def preprocess(self):
        self.init_manager.ensure_initialized()
        df = self.init_manager.df
        try:
            df.rename(columns={"old_name_D1": "new_name_D1"}, inplace=True)
            df.drop(columns=["unnecessary_column_D"], inplace=True)
            logging.info("ProcessorD: 前処理が完了しました。")
        except KeyError as e:
            logging.error(f"ProcessorD: 前処理中にエラーが発生しました。{e}")
            raise


class ProcessorE(BaseProcessor):
    def preprocess(self):
        self.init_manager.ensure_initialized()
        df = self.init_manager.df
        try:
            df.rename(columns={"old_name_E1": "new_name_E1"}, inplace=True)
            df.drop(columns=["unnecessary_column_E"], inplace=True)
            logging.info("ProcessorE: 前処理が完了しました。")
        except KeyError as e:
            logging.error(f"ProcessorE: 前処理中にエラーが発生しました。{e}")
            raise


class FinalProcessor:
    """FinalProcessor: 全ての前処理が完了したDataFrameを結合"""

    def __init__(self, processors: list):
        self.processors = processors

    def run_all_preprocessing(self):
        for processor in self.processors:
            processor.preprocess()

    def merge_dataframes(self, on: str):
        merged_df = None
        for processor in self.processors:
            if merged_df is None:
                merged_df = processor.init_manager.df
            else:
                # 結合キー 'on' を基に結合
                merged_df = pd.merge(
                    merged_df, processor.init_manager.df, on=on, how="outer"
                )
        logging.info("FinalProcessor: 全てのDataFrameの結合が完了しました。")
        return merged_df


# 使用例
if __name__ == "__main__":
    # 初期データの作成
    data_a = {"old_name_A1": [1, 2, 3], "unnecessary_column_A": ["x", "y", "z"]}
    df_a = pd.DataFrame(data_a)

    data_b = {"old_name_B1": [4, 5, 6], "unnecessary_column_B": ["a", "b", "c"]}
    df_b = pd.DataFrame(data_b)

    data_c = {"old_name_C1": [7, 8, 9], "unnecessary_column_C": ["d", "e", "f"]}
    df_c = pd.DataFrame(data_c)

    data_d = {"old_name_D1": [10, 11, 12], "unnecessary_column_D": ["g", "h", "i"]}
    df_d = pd.DataFrame(data_d)

    data_e = {"old_name_E1": [13, 14, 15], "unnecessary_column_E": ["j", "k", "l"]}
    df_e = pd.DataFrame(data_e)

    # InitializationManagerのインスタンス作成
    init_manager_a = InitializationManager(df_a)
    init_manager_b = InitializationManager(df_b)
    init_manager_c = InitializationManager(df_c)
    init_manager_d = InitializationManager(df_d)
    init_manager_e = InitializationManager(df_e)

    # 各プロセッサのインスタンス作成
    processor_a = ProcessorA(init_manager_a)
    processor_b = ProcessorB(init_manager_b)
    processor_c = ProcessorC(init_manager_c)
    processor_d = ProcessorD(init_manager_d)
    processor_e = ProcessorE(init_manager_e)

    # プロセッサをリストにまとめる
    processors = [processor_a, processor_b, processor_c, processor_d, processor_e]

    # FinalProcessorのインスタンス作成
    final_processor = FinalProcessor(processors)

    # 全ての前処理を実行
    final_processor.run_all_preprocessing()

    # DataFrameの結合
    # 結合キー 'new_name_A1' と 'new_name_B1' が共通キーであると仮定
    # 実際のデータに合わせて結合キーを設定してください
    # ここでは単純に縦方向に結合（concat）する例を示します
    merged_df = pd.concat([p.init_manager.df for p in processors], ignore_index=True)
    logging.info("FinalProcessor: 全てのDataFrameを縦方向に結合しました。")
    print(merged_df)
