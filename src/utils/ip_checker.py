import pandas as pd
import ipaddress
from typing import Union, List, Optional

def check_ip_in_subnet(
    ip_df: pd.DataFrame,
    subnet_df: pd.DataFrame,
    ip_column: str = 'ip',
    subnet_column: str = 'subnet',
    additional_columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    IPアドレスがどのサブネットに属しているか判定する関数
    
    Parameters:
    -----------
    ip_df : pd.DataFrame
        IPアドレスのリストを含むDataFrame
    subnet_df : pd.DataFrame
        サブネットのリストを含むDataFrame
    ip_column : str
        IPアドレスが格納されている列名
    subnet_column : str
        サブネットが格納されている列名
    additional_columns : List[str], optional
        サブネットDFから追加で取得したい列名のリスト
        
    Returns:
    --------
    pd.DataFrame
        各IPアドレスに対応するサブネット情報を含むDataFrame
    """
    
    def is_ip_in_subnet(ip: str, subnet: str) -> bool:
        try:
            return ipaddress.ip_address(ip) in ipaddress.ip_network(subnet)
        except ValueError:
            return False

    # 結果を格納するリスト
    results = []
    
    # 各IPアドレスに対して判定
    for _, ip_row in ip_df.iterrows():
        ip = ip_row[ip_column]
        matched = False
        
        for _, subnet_row in subnet_df.iterrows():
            subnet = subnet_row[subnet_column]
            
            if is_ip_in_subnet(ip, subnet):
                # 基本情報の辞書を作成
                result_dict = {
                    'ip': ip,
                    'matching_subnet': subnet
                }
                
                # 追加の列がある場合は追加
                if additional_columns:
                    for col in additional_columns:
                        result_dict[col] = subnet_row[col]
                        
                results.append(result_dict)
                matched = True
                break
        
        # マッチするサブネットが見つからなかった場合
        if not matched:
            result_dict = {
                'ip': ip,
                'matching_subnet': None
            }
            if additional_columns:
                for col in additional_columns:
                    result_dict[col] = None
            results.append(result_dict)
    
    return pd.DataFrame(results)

# 使用例
if __name__ == "__main__":
    # サンプルデータの作成
    ip_data = {
        'ip': [
            '192.168.1.100',
            '10.0.0.50',
            '172.16.0.1',
            '8.8.8.8'
        ]
    }
    
    subnet_data = {
        'subnet': [
            '192.168.1.0/24',
            '10.0.0.0/16',
            '172.16.0.0/12'
        ],
        'network_name': [
            'Office Network',
            'Development Network',
            'Management Network'
        ]
    }
    
    ip_df = pd.DataFrame(ip_data)
    subnet_df = pd.DataFrame(subnet_data)
    
    # 関数の実行
    result = check_ip_in_subnet(
        ip_df,
        subnet_df,
        additional_columns=['network_name']
    )
    
    print("結果:")
    print(result)