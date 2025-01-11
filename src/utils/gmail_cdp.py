from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import sys

class GmailAutomatorPlaywright:
    def __init__(self, user_agent='Default User Agent', timeout=10000):
        self.user_agent = user_agent
        self.timeout = timeout  # ミリ秒
        self.current_step = "初期化中"
        self.browser = None
        self.context = None
        self.page = None
        self._initialize_browser()

    def _initialize_browser(self):
        self.current_step = "ブラウザの初期化"
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=False, args=[f"--user-agent={self.user_agent}"])
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        print("ブラウザが初期化されました。")

    def wait_for_selector(self, selector, timeout=None):
        if timeout is None:
            timeout = self.timeout
        self.current_step = f"セレクタを待機中: {selector}"
        try:
            element = self.page.wait_for_selector(selector, timeout=timeout)
            if not element:
                raise PlaywrightTimeoutError(f"セレクタが見つかりませんでした: {selector}")
            print(f"セレクタが見つかりました: {selector}")
            return element
        except PlaywrightTimeoutError as e:
            self.current_step = f"エラー: セレクタが見つかりませんでした - {selector}"
            print(f"エラー: セレクタが見つかりませんでした - {selector}")
            self.close()
            sys.exit(1)

    def get_element_text(self, selector, timeout=None):
        element = self.wait_for_selector(selector, timeout)
        text = element.inner_text()
        print(f"要素のテキスト取得: {text}")
        return text

    def login(self, email, password):
        try:
            self.current_step = "Gmailのログインページに移動"
            self.page.goto('https://accounts.google.com/signin')
            print("Gmailのログインページに移動しました。")

            # メールアドレスを入力
            email_input = self.wait_for_selector('input#identifierId')
            email_input.fill(email)
            next_button = self.wait_for_selector('button#identifierNext')
            next_button.click()
            print("メールアドレスを入力し、次へボタンをクリックしました。")

            # パスワードを入力
            password_input = self.wait_for_selector('input[name="password"]', timeout=15000)
            password_input.fill(password)
            pass_next_button = self.wait_for_selector('button#passwordNext')
            pass_next_button.click()
            print("パスワードを入力し、次へボタンをクリックしました。")

            # ログインが完了するまで待機
            self.current_step = "ログイン完了の確認"
            self.wait_for_selector('a[href*="SignOutOptions"]', timeout=20000)
            print("ログインが完了しました。")

            # 新しいタブを開く
            self.current_step = "受信トレイに移動"
            inbox_page = self.context.new_page()
            inbox_page.goto('https://mail.google.com/mail/u/0/#inbox')
            print("新しいタブで受信トレイに移動しました。")

        except PlaywrightTimeoutError as e:
            print(f"エラーが発生しました: {e}")
            print(f"現在のステップ: {self.current_step}")
            self.close()
            sys.exit(1)

    def close(self):
        self.current_step = "ブラウザを閉じる"
        if self.browser:
            self.browser.close()
            print("ブラウザを閉じました。")

# --- 使用例 ---
if __name__ == "__main__":
    USER_AGENT = 'Your Custom User Agent'
    EMAIL = 'your_email@gmail.com'
    PASSWORD = 'your_password'

    automator = GmailAutomatorPlaywright(user_agent=USER_AGENT)
    automator.login(email=EMAIL, password=PASSWORD)
    
    # 特定の要素のテキストを取得する例
    # element_text = automator.get_element_text('.your-class-name')
    # print(f"取得したテキスト: {element_text}")

    # ブラウザを閉じる
    automator.close()