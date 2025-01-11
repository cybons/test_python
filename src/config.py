import yaml


class Config:
    def __init__(self, config_path):
        with open(config_path, "r", encoding="utf-8") as file:
            self.config = yaml.safe_load(file)

    def get(self, key, default=None):
        return self.config.get(key, default)
