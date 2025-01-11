import os

def resolve_paths(config: dict, base_path: str) -> dict:
    """辞書内の 'paths' キー配下の相対パスを絶対パスに変換します。"""
    base_dir = os.path.dirname(base_path)
    
    def resolve_relative_path(value):
        if isinstance(value, str):
            return os.path.abspath(os.path.join(base_dir, value))
        elif isinstance(value, dict):
            return {k: resolve_relative_path(v) for k, v in value.items()}
        else:
            return value

    def traverse(config_dict, under_paths=False):
        if isinstance(config_dict, dict):
            resolved = {}
            for k, v in config_dict.items():
                # 'paths' キーに到達したらフラグを立てる
                if k == 'paths':
                    resolved[k] = resolve_relative_path(v)
                else:
                    # 再帰的に探索
                    resolved[k] = traverse(v, under_paths)
            return resolved
        elif under_paths:
            return resolve_relative_path(config_dict)
        else:
            return config_dict

    return traverse(config)

# 使用例
if __name__ == "__main__":
    sample_config = {
        "database": {
            "host": "localhost",
            "port": 5432
        },
        "paths": {
            "data_file": "data/input.csv",
            "log_file": "logs/app.log"
        },
        "other": {
            "nested": {
                "paths": {
                    "config": "configs/settings.yaml"
                }
            }
        }
    }

    base_path = "/home/user/project/config/settings.yaml"
    resolved_config = resolve_paths(sample_config, base_path)
    print(resolved_config)