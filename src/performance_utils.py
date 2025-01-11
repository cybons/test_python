import time
from functools import wraps

def timeit(deci=1):
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