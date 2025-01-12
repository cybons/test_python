sequenceDiagram
    actor HR as 人事部門<br>(WLS)
    participant Admin as データ管理者<br>(社内SS)
    participant IT as システム部門<br>(GOD)
    participant WEVOX as WEVOXシステム

    Note over HR,WEVOX: 月初5営業日以内に開始
    
    %% 申請データ提供フェーズ
    HR->>+Admin: 申請書の提供<br>(配信申請・閲覧権限申請)
    HR->>Admin: 休職・産休育休リストの提供
    
    %% データ確認フェーズ
    activate Admin
    Admin->>Admin: データチェック<br>1. フォーマット確認<br>2. 必須項目確認<br>3. 組織コード確認
    
    alt データに問題がある場合
        Admin-->>HR: 修正依頼
        HR->>Admin: 修正データ提供
    end
    deactivate Admin

    %% システム更新フェーズ
    Note over Admin,IT: 15-16日頃までに完了
    Admin->>+IT: GODデータ更新要求
    IT->>+WEVOX: データインポート処理
    
    alt インポートエラー発生
        WEVOX-->>IT: エラー通知
        IT->>IT: エラー原因調査
        IT->>WEVOX: 再インポート
    end
    
    WEVOX-->>-IT: インポート完了通知
    IT-->>-Admin: 更新完了報告

    %% 直接データ処理フェーズ
    opt WEVOXシステムからの要求がある場合
        WEVOX->>+Admin: データ要求
        Admin->>Admin: データ作成・確認
        Admin->>WEVOX: データ提供
        WEVOX-->>-Admin: 受領確認
    end

    Note over HR,WEVOX: 月末までに完了

    %% 完了確認フェーズ
    Admin->>Admin: 最終確認<br>1. 組織更新確認<br>2. 配信設定確認