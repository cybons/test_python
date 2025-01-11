import pandas as pd

class AdminUsersProcessor:
    """
    システムエクスポートデータからadmin_usersを作成するクラス
    """
    def __init__(self):
        self.users_df = None
        self.userapp_df = None
        self.location_df = None
        self.user_org_title_df = None
        self.org_df = None
        self.title_df = None

    def load_data(self, data_files: dict) -> None:
        """
        必要なCSVファイルを読み込む

        Parameters:
        data_files (dict): ファイルパスを含む辞書
            {
                'user': 'path/to/user.csv',
                'userapp': 'path/to/userapp.csv',
                'location': 'path/to/location.csv',
                'user_org_title': 'path/to/user_org_title.csv',
                'org': 'path/to/org.csv',
                'title': 'path/to/title.csv'
            }
        """
        self.users_df = pd.read_csv(data_files['user'])
        self.userapp_df = pd.read_csv(data_files['userapp'])
        self.location_df = pd.read_csv(data_files['location'])
        self.user_org_title_df = pd.read_csv(data_files['user_org_title'])
        self.org_df = pd.read_csv(data_files['org'])
        self.title_df = pd.read_csv(data_files['title'])

    def process_admin_users(self) -> pd.DataFrame:
        """
        admin_users用のデータを作成する
        
        Returns:
        pd.DataFrame: 処理済みのadmin_usersデータ
        """
        # 社外送受信権限を持つユーザーを抽出
        email_users = self.userapp_df[
            self.userapp_df['application_code'] == 'EMAIL01'
        ]['user_code'].unique()

        # 主務の組織情報を抽出（フラグ=1）
        primary_orgs = self.user_org_title_df[
            self.user_org_title_df['primary_flag'] == 1
        ]

        # ユーザー基本情報の作成
        admin_users = self.users_df.merge(
            self.location_df,
            on='user_code',
            how='left'
        )

        # 社外メール権限フラグの追加
        admin_users['has_external_email'] = admin_users['user_code'].isin(email_users)

        # 組織情報の結合
        admin_users = admin_users.merge(
            primary_orgs,
            on='user_code',
            how='left'
        )

        # 組織マスタとの結合
        admin_users = admin_users.merge(
            self.org_df,
            on='org_code',
            how='left'
        )

        # 役職情報の結合
        admin_users = admin_users.merge(
            self.title_df,
            on='title_code',
            how='left'
        )

        # 必要な列の選択と名前の変更
        admin_users = admin_users[[
            'user_code',
            'user_name',
            'org_code',
            'org_name',
            'title_name',
            'location_name',
            'has_external_email'
        ]]

        return admin_users

    def validate_data(self, admin_users: pd.DataFrame) -> List[str]:
        """
        作成したデータのバリデーションを行う

        Parameters:
        admin_users (pd.DataFrame): 検証するデータフレーム

        Returns:
        List[str]: エラーメッセージのリスト
        """
        errors = []

        # 必須項目のチェック
        required_columns = [
            'user_code', 'user_name', 'org_code', 'org_name'
        ]
        for col in required_columns:
            if admin_users[col].isna().any():
                null_users = admin_users[admin_users[col].isna()]['user_code'].tolist()
                errors.append(f"{col}が未設定のユーザーがいます: {null_users}")

        # 社外メール権限を持つユーザーの必須チェック
        email_users = admin_users[admin_users['has_external_email']]
        if email_users['location_name'].isna().any():
            null_locations = email_users[
                email_users['location_name'].isna()
            ]['user_code'].tolist()
            errors.append(
                f"社外メール権限を持つユーザーで場所情報が未設定です: {null_locations}"
            )

        return errors

    def export_to_excel(
        self,
        admin_users: pd.DataFrame,
        output_path: str
    ) -> None:
        """
        処理したデータをExcelファイルとして出力

        Parameters:
        admin_users (pd.DataFrame): 出力するデータフレーム
        output_path (str): 出力先のパス
        """
        writer = pd.ExcelWriter(output_path, engine='openpyxl')
        admin_users.to_excel(
            writer,
            sheet_name='admin_users',
            index=False
        )
        writer.save()

# 使用例
if __name__ == "__main__":
    # ファイルパスの設定
    data_files = {
        'user': 'user.csv',
        'userapp': 'userapp.csv',
        'location': 'location.csv',
        'user_org_title': 'user_org_title.csv',
        'org': 'org.csv',
        'title': 'title.csv'
    }

    # プロセッサーの初期化と実行
    processor = AdminUsersProcessor()
    processor.load_data(data_files)
    
    # admin_usersの作成
    admin_users = processor.process_admin_users()

    # バリデーション
    errors = processor.validate_data(admin_users)
    if errors:
        print("以下のエラーが検出されました:")
        for error in errors:
            print(f"- {error}")
    
    # エクスポート
    processor.export_to_excel(admin_users, 'admin_users.xlsx')