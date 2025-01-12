from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys

class GmailAutomatorSelenium:
    def __init__(self, driver_path, user_agent='Default User Agent', timeout=10):
        self.driver_path = driver_path
        self.user_agent = user_agent
        self.timeout = timeout
        self.current_step = "初期化中"
        self.driver = None
        self._initialize_driver()

    def _initialize_driver(self):
        self.current_step = "ドライバーの初期化"
        chrome_options = Options()
        chrome_options.add_argument(f'--user-agent={self.user_agent}')
        chrome_options.add_argument('--start-maximized')
        # 既存のプロファイルを使用する場合は以下をコメント解除
        # chrome_options.add_argument("user-data-dir=C:/Path/To/Your/Chrome/Profile")
        # chrome_options.add_argument("profile-directory=Default")

        service = Service(executable_path=self.driver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        print("ドライバーが初期化されました。")

    def wait_for_element(self, by, identifier, timeout=None):
        if timeout is None:
            timeout = self.timeout
        self.current_step = f"要素を待機中: {identifier}"
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, identifier))
            )
            print(f"要素が見つかりました: {identifier}")
            return element
        except Exception as e:
            self.current_step = f"エラー: 要素が見つかりませんでした - {identifier}"
            print(f"エラー: 要素が見つかりませんでした - {identifier}")
            self.driver.quit()
            sys.exit(1)

    def get_element_text(self, by, identifier, timeout=None):
        element = self.wait_for_element(by, identifier, timeout)
        text = element.text
        print(f"要素のテキスト取得: {text}")
        return text

    def login(self, email, password):
        try:
            self.current_step = "Gmailのログインページに移動"
            self.driver.get('https://accounts.google.com/signin')
            print("Gmailのログインページに移動しました。")

            # メールアドレスを入力
            email_input = self.wait_for_element(By.ID, 'identifierId')
            email_input.send_keys(email)
            next_button = self.wait_for_element(By.ID, 'identifierNext')
            next_button.click()
            print("メールアドレスを入力し、次へボタンをクリックしました。")

            # パスワードを入力
            password_input = self.wait_for_element(By.NAME, 'password', timeout=15)
            password_input.send_keys(password)
            pass_next_button = self.wait_for_element(By.ID, 'passwordNext')
            pass_next_button.click()
            print("パスワードを入力し、次へボタンをクリックしました。")

            # ログインが完了するまで待機
            self.current_step = "ログイン完了の確認"
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="SignOutOptions"]'))
            )
            print("ログインが完了しました。")

            # 新しいタブを開く
            self.current_step = "受信トレイに移動"
            self.driver.execute_script("window.open('https://mail.google.com/mail/u/0/#inbox', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[1])
            print("新しいタブで受信トレイに移動しました。")

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            print(f"現在のステップ: {self.current_step}")
            self.driver.quit()
            sys.exit(1)

    def close(self):
        self.current_step = "ドライバーを閉じる"
        self.driver.quit()
        print("ドライバーを閉じました。")

# --- 使用例 ---
if __name__ == "__main__":
    DRIVER_PATH = '/path/to/chromedriver'  # 例: 'C:/drivers/chromedriver.exe'
    USER_AGENT = 'Your Custom User Agent'
    EMAIL = 'your_email@gmail.com'
    PASSWORD = 'your_password'

    automator = GmailAutomatorSelenium(driver_path=DRIVER_PATH, user_agent=USER_AGENT)
    automator.login(email=EMAIL, password=PASSWORD)
    
    # 特定の要素のテキストを取得する例
    # element_text = automator.get_element_text(By.CLASS_NAME, 'your-class-name')
    # print(f"取得したテキスト: {element_text}")

    # ブラウザを閉じる
    automator.close()