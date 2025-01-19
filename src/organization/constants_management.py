# アプローチ1: 名前空間を使用した定数管理
class WevoxConstants:
    """WEVOXシステムで使用する定数を管理するクラス"""

    class Sheet:
        """シート名に関する定数"""

        DELIVERY_ORG = "配信組織"

    class Column:
        """列名に関する定数"""

        # 共通
        EMAIL = "メールアドレス"
        EMPLOYEE_ID = "社員番号"

        # 配信組織シート
        ORG_CODE = "組織コード"
        INCLUDE_SUB = "配下含む"
        REGULAR_EMPLOYEE = "正社員含む"
        CONTRACT_EMPLOYEE = "契約社員含む"
        TEMP_EMPLOYEE = "派遣社員含む"

        # 配信フラグファイル
        DELIVERY_FLAG = "配信"

    class Value:
        """値に関する定数"""

        TRUE = "TRUE"
        FALSE = "FALSE"
        NO = "いいえ"

    class EmploymentType:
        """雇用形態に関する定数"""

        REGULAR = "正社員"
        CONTRACT = "契約社員"
        TEMP = "派遣社員"


# 使用例
def example_usage():
    # アプローチ1の使用例
    print(WevoxConstants.Column.EMAIL)  # "メールアドレス"
    print(WevoxConstants.Value.TRUE)  # "TRUE"


example_usage()
