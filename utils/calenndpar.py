import datetime
import os.path
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Google Calendar APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def authenticate_google_calendar():
    """Google Calendar APIに認証し、サービスオブジェクトを返す"""
    creds = None
    # token.jsonが存在すれば、それを使用して認証
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # 認証情報がないか、無効な場合は再認証
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # トークンを保存
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('calendar', 'v3', credentials=creds)
    return service

def fetch_calendar_events(service, calendar_id, time_min, time_max):
    """指定された期間内のカレンダーイベントを取得する"""
    events = []
    page_token = None
    while True:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat() + 'Z',
            timeMax=time_max.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime',
            pageToken=page_token
        ).execute()
        events.extend(events_result.get('items', []))
        page_token = events_result.get('nextPageToken')
        if not page_token:
            break
    return events

def calculate_time_difference(start_time_str, end_time_str):
    """開始時間と終了時間の差分を「HH:MM」形式で返す"""
    fmt = '%H:%M'
    start_time = datetime.datetime.strptime(start_time_str, fmt)
    end_time = datetime.datetime.strptime(end_time_str, fmt)
    delta = end_time - start_time
    if delta.days < 0:
        delta += datetime.timedelta(days=1)
    hours, remainder = divmod(delta.seconds, 3600)
    minutes = remainder // 60
    return f"{hours:02}:{minutes:02}"

def process_events(events):
    """イベントデータを処理し、必要な情報を抽出する"""
    processed_data = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        summary = event.get('summary', 'No Title')
        # 日付と時間を分割
        start_dt = datetime.datetime.fromisoformat(start)
        end_dt = datetime.datetime.fromisoformat(end)
        # 日付を文字列に変換
        start_date = start_dt.strftime('%Y/%m/%d')
        end_date = end_dt.strftime('%Y/%m/%d')
        # 時間を「HH:MM」形式で取得
        start_time = start_dt.strftime('%H:%M')
        end_time = end_dt.strftime('%H:%M')
        # 時間差分の計算
        duration = calculate_time_difference(start_time, end_time)
        processed_data.append({
            '開始日': start_date,
            '終了日': end_date,
            '開始時間': start_time,
            '終了時間': end_time,
            'タイトル': summary,
            '期間': duration
        })
    return processed_data

def save_to_excel(data, filename='calendar_events.xlsx'):
    """処理したデータをExcelファイルに保存する"""
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"データを {filename} に保存しました。")

def main():
    # 認証
    service = authenticate_google_calendar()
    
    # カレンダーIDの設定（通常は 'primary' が自身のカレンダー）
    calendar_id = 'primary'  # または特定のカレンダーID
    
    # 取得期間の設定（例: 2023/01/01 から 2024/11/30）
    time_min = datetime.datetime(2023, 1, 1, 0, 0, 0)
    time_max = datetime.datetime(2024, 11, 30, 23, 59, 59)
    
    # イベントの取得
    print("イベントを取得中...")
    events = fetch_calendar_events(service, calendar_id, time_min, time_max)
    print(f"取得したイベント数: {len(events)}")
    
    if not events:
        print("指定された期間内にイベントが見つかりませんでした。")
        return
    
    # イベントの処理
    print("イベントを処理中...")
    processed_data = process_events(events)
    
    # Excelへの保存
    print("Excelファイルに保存中...")
    save_to_excel(processed_data)

if __name__ == '__main__':
    main()