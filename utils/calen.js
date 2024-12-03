// メインのバッチ処理関数
function processBatch() {
  const sheetName = 'BatchProcessing'; // シート名を指定
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(sheetName);
  const dataRange = sheet.getDataRange();
  const data = dataRange.getValues();
  
  // ヘッダーをスキップ
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const startDate = row[0];
    const endDate = row[1];
    const deviceId = row[2];
    let status = row[3];
    const errorMsg = row[4];
    
    if (status === '未処理' || status === 'エラー') {
      // ステータスを「処理中」に更新
      sheet.getRange(i + 1, 4).setValue('処理中');
      
      try {
        // データ抽出処理を実行
        const reservations = extractReservations(deviceId, startDate, endDate);
        
        // 抽出データを別シートに保存（例: "Reservations" シート）
        const reservationsSheet = ss.getSheetByName('Reservations') || ss.insertSheet('Reservations');
        reservationsSheet.appendRow([deviceId, startDate, endDate, JSON.stringify(reservations)]);
        
        // ステータスを「完了」に更新
        sheet.getRange(i + 1, 4).setValue('完了');
      } catch (error) {
        // エラー発生時の処理
        sheet.getRange(i + 1, 4).setValue('エラー');
        sheet.getRange(i + 1, 5).setValue(error.toString());
        Logger.log(`Error processing row ${i + 1}: ${error}`);
      }
      
      // 実行時間を考慮して一定数処理したら終了
      // ここでは例として5件ごとに終了
      if ((i - 1) % 5 === 0 && i !== 1) {
        // 次のバッチをトリガー
        ScriptApp.newTrigger('processBatch')
          .timeBased()
          .after(1000) // 1秒後に次のバッチを実行
          .create();
        return;
      }
    }
  }
  
  Logger.log('全てのバッチが完了しました。');
}



// 設備予約データを抽出する関数（例）
function extractReservations(deviceId, startDate, endDate) {
  // ここで実際のデータソースから予約データを取得します
  // 例として、架空のAPIからデータを取得する場合
  /*
  const response = UrlFetchApp.fetch(`https://api.example.com/reservations?device=${deviceId}&start=${startDate}&end=${endDate}`);
  const data = JSON.parse(response.getContentText());
  return data.reservations;
  */
  
  // 仮のデータを返す例
  const dummyData = [
    { reservationId: 1, deviceId: deviceId, start: startDate, end: endDate, user: 'User A' },
    { reservationId: 2, deviceId: deviceId, start: startDate, end: endDate, user: 'User B' },
  ];
  
  // 実際のデータ取得ロジックに置き換えてください
  return dummyData;
}


// カスタムメニューを追加
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('バッチ処理')
    .addItem('処理を開始', 'startBatchProcessing')
    .addToUi();
}

// バッチ処理を開始する関数
function startBatchProcessing() {
  // 既存のトリガーを削除して重複実行を防ぐ
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'processBatch') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  
  // バッチ処理を開始
  processBatch();
}


// 全てのバッチトリガーを削除
function deleteAllBatchTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'processBatch') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
}

/**
 * バッチ処理リストを作成する関数
 */
function createBatchList() {
  const equipmentSheetName = 'EquipmentList'; // 設備IDがリストされているシート名
  const batchSheetName = 'BatchProcessing'; // バッチ処理リストを生成するシート名
  const startDate = new Date('2023-01-01'); // 開始日
  const endDate = new Date('2024-11-30'); // 終了日
  const periodMonths = 2; // 期間の月数（今回は2か月）
  
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const equipmentSheet = ss.getSheetByName(equipmentSheetName);
  const batchSheet = ss.getSheetByName(batchSheetName) || ss.insertSheet(batchSheetName);
  
  // 設備IDを取得
  const equipmentData = equipmentSheet.getRange('A2:A').getValues();
  const equipmentIDs = equipmentData.flat().filter(id => id); // 空白を除去
  
  if (equipmentIDs.length === 0) {
    SpreadsheetApp.getUi().alert('EquipmentListシートに設備IDが存在しません。');
    return;
  }
  
  // BatchProcessingシートをクリアしてヘッダーを設定
  batchSheet.clearContents();
  batchSheet.appendRow(['開始日', '終了日', '設備ID', 'ステータス', 'エラーメッセージ']);
  
  // 期間を分割してリストを生成
  let currentStartDate = new Date(startDate);
  while (currentStartDate <= endDate) {
    // 次の期間の終了日を計算
    let currentEndDate = new Date(currentStartDate);
    currentEndDate.setMonth(currentEndDate.getMonth() + periodMonths);
    currentEndDate.setDate(0); // 前月の最終日
    
    // 終了日が全体の終了日を超えないように調整
    if (currentEndDate > endDate) {
      currentEndDate = new Date(endDate);
    }
    
    // 設備IDごとにリストを作成
    equipmentIDs.forEach(deviceId => {
      batchSheet.appendRow([
        formatDate(currentStartDate),
        formatDate(currentEndDate),
        deviceId,
        '未処理',
        ''
      ]);
    });
    
    // 次の期間の開始日を設定
    currentStartDate = new Date(currentEndDate);
    currentStartDate.setDate(currentStartDate.getDate() + 1); // 翌日から開始
  }
  
  SpreadsheetApp.getUi().alert('バッチ処理リストの作成が完了しました。');
}

/**
 * 日付をYYYY/MM/DD形式の文字列にフォーマットする関数
 * @param {Date} date 
 * @returns {string}
 */
function formatDate(date) {
  const year = date.getFullYear();
  const month = ('0' + (date.getMonth() + 1)).slice(-2); // 月は0始まり
  const day = ('0' + date.getDate()).slice(-2);
  return `${year}/${month}/${day}`;
}

/**
 * カスタムメニューを追加する関数
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('バッチ処理')
    .addItem('バッチリストを作成', 'createBatchList')
    .addToUi();
}