import json
import os
from logging import config, getLogger

import pandas as pd
from data_loader import load_config
from data_processing import (
    process_location_data,
    process_organization_data,
    process_user_data,
    process_usergroup_data,
)
from organization import create_organization


def main():
    base_dir = os.path.dirname(__file__)

    with open(os.path.join(base_dir, "conf", "./log_config.json"), "r") as f:
        log_conf = json.load(f)

    config.dictConfig(log_conf)
    logger = getLogger(__name__)
    # paths = get_file_paths(base_dir)

    df = pd.read_excel(os.path.join(base_dir, "org.xlsx"))

    # df_mapping = pd.read_excel(os.path.join(baseDir, "mapping.xlsx"))

    mapping_data = {
        "org_code": [
            "02HR",
        ],
        "org_name": [
            "Human Resources",
        ],
        "abbreviation": ["HR"],  # 括弧なし
    }

    df_mapping = pd.DataFrame(mapping_data)

    # Excelファイルからマッピングデータを読み込む場合は、以下を使用
    # excel_path = "path_to_mapping_excel.xlsx"
    # mapping_dict = prepare_mapping_table(excel_path=excel_path)

    org_data = create_organization(df, df_mapping=df_mapping)
    print(org_data)
    # ここでローカルファイルを使って4つのマスタデータを作成する
    # DFが3つ出来上がる。

    # paths = get_file_paths(base_dir)
    paths = load_config(
        os.path.join(base_dir, "conf", "file_path.yaml"), encoding="utf8"
    )
    # 1. まず事業所を作る
    location = process_location_data(paths)

    # 2. 組織を作る
    org = process_organization_data(paths, location)

    # 3. ユーザーを作る
    user = process_user_data(paths, org, location)

    # 4. ユーザーグループを作る
    process_usergroup_data(paths, user)

    # 4つのDFをエクスポートする
    # これはそれぞれのprocess_関数で実施した方がいいかな。

    logger.info("正常終了")


if __name__ == "__main__":
    main()
