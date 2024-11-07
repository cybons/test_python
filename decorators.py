import time
import logging
from functools import wraps
import inspect

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
                    logging.warning(f"{func.__name__} でエラー発生: {e} (試行 {attempt}/{times})")
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
                    raise TypeError(f"引数 '{name}' は {expected_type} 型でなければなりません。")
            for key, value in kwargs.items():
                if key in type_hints and not isinstance(value, type_hints[key]):
                    raise TypeError(f"引数 '{key}' は {type_hints[key]} 型でなければなりません。")
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
                    raise TypeError(f"引数 '{name}' は {expected_type} 型でなければなりません。")
        
        result = func(*args, **kwargs)
        
        if 'return' in func.__annotations__:
            expected_return_type = func.__annotations__['return']
            if not isinstance(result, expected_return_type):
                raise TypeError(f"戻り値は {expected_return_type} 型でなければなりません。")
        
        return result
    return wrapper