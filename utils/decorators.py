import inspect
import io
import logging
import time
from functools import wraps
from pathlib import Path

import pandas as pd
from exceptions.custom_exceptions import UserProcessorError

logger = logging.getLogger(__name__)


# ログデコレーター
def log_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.info(f"関数 '{func.__name__}' が呼び出されました。")
        logging.info(f"引数: args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        logging.info(f"関数 '{func.__name__}' の戻り値: {result}")
        return result

    return wrapper


# キャッシュデコレーター
def memoize(func):
    cache = {}

    @wraps(func)
    def wrapper(*args):
        if args in cache:
            print(f"キャッシュから取得: {func.__name__}{args} = {cache[args]}")
            return cache[args]
        result = func(*args)
        cache[args] = result
        print(f"計算してキャッシュに保存: {func.__name__}{args} = {result}")
        return result

    return wrapper


# リトライデコレーター
def retry(times=3, delay=1, exceptions=(Exception,)):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    logging.warning(
                        f"{func.__name__} でエラー発生: {e} (試行 {attempt}/{times})"
                    )
                    if attempt < times:
                        time.sleep(delay)
                    else:
                        logging.error(f"{func.__name__} が全ての試行で失敗しました。")
                        raise

        return wrapper

    return decorator


# 入力検証デコレーター
def validate_types(**type_hints):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for arg, (name, expected_type) in zip(args, type_hints.items()):
                if not isinstance(arg, expected_type):
                    raise TypeError(
                        f"引数 '{name}' は {expected_type} 型でなければなりません。"
                    )
            for key, value in kwargs.items():
                if key in type_hints and not isinstance(value, type_hints[key]):
                    raise TypeError(
                        f"引数 '{key}' は {type_hints[key]} 型でなければなりません。"
                    )
            return func(*args, **kwargs)

        return wrapper

    return decorator


# シングルトンデコレーター
def singleton(cls):
    instances = {}

    @wraps(cls)
    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return wrapper


# デバッグデコレーター
def debug(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"呼び出し: {func.__name__}()")
        print(f"引数: args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"戻り値: {result}")
        return result

    return wrapper


# タイプチェックデコレーター
def type_check(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        for name, value in bound_args.arguments.items():
            if name in func.__annotations__:
                expected_type = func.__annotations__[name]
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"引数 '{name}' は {expected_type} 型でなければなりません。"
                    )

        result = func(*args, **kwargs)

        if "return" in func.__annotations__:
            expected_return_type = func.__annotations__["return"]
            if not isinstance(result, expected_return_type):
                raise TypeError(
                    f"戻り値は {expected_return_type} 型でなければなりません。"
                )

        return result

    return wrapper


def deco_measure(deci=1):
    """
    関数の実行時間を計測するデコレーター。

    Args:
        deci (int): 出力する小数点以下の桁数。デフォルトは1。

    Returns:
        function: デコレートされた関数。
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                end = time.perf_counter()
                elapsed = end - start
                print(f"{func.__name__} 処理時間: {elapsed:.{deci}f} 秒")

        return wrapper

    return decorator


@deco_measure
def get_filtered_file_list(directory):
    path = Path(directory)
    filtered_files = [
        file.name
        for file in path.glob("*")
        if file.is_file() and not file.name.startswith("~$")
    ]
    return filtered_files


def log_dataframe_info(df: pd.DataFrame, df_name: str):
    logger.info(f"DataFrame '{df_name}' の情報:")
    logger.info(f"行数: {len(df)}, 列数: {df.shape[1]}")

    # df.info()の内容をログに出力
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_str = buffer.getvalue()
    logger.debug(f"DataFrame '{df_name}' の詳細情報:\n{info_str}")

    # 追加情報（必要に応じて）
    logger.debug(f"DataFrame '{df_name}' のメモリ使用量:\n{df.memory_usage(deep=True)}")
    logger.debug(f"DataFrame '{df_name}' の基本統計量:\n{df.describe(include='all')}")


def handle_errors(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except UserProcessorError as e:
            self._handle_error(e)
        except Exception as e:
            logging.error(
                f"Unexpected error in {method.__name__} of {self.dataframe_name}: {e}"
            )
            self._handle_error(e)

    return wrapper
