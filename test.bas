Sub SelectNoFillCells_UsingArray()
    Dim rng As Range
    Dim cell As Range
    Dim noFillRange As Range
    Dim arr As Variant
    Dim i As Long, j As Long
    Dim ws As Worksheet
    
    ' 対象のシートを設定（必要に応じて変更）
    Set ws = ThisWorkbook.Sheets("入力表")
    
    ' 列B全体を対象に設定
    Set rng = ws.Columns("B:B")
    
    ' 配列にセルのColorIndexを読み込む
    arr = rng.Interior.ColorIndex
    
    ' 配列をループして塗りつぶしなしのセルを特定
    For i = 1 To UBound(arr, 1)
        If arr(i, 1) = xlColorIndexNone Or IsEmpty(arr(i, 1)) Then
            If noFillRange Is Nothing Then
                Set noFillRange = rng.Cells(i, 1)
            Else
                Set noFillRange = Union(noFillRange, rng.Cells(i, 1))
            End If
        End If
    Next i
    
    ' 結果を選択
    If Not noFillRange Is Nothing Then
        noFillRange.Select
        MsgBox "背景色が設定されていないセルを " & noFillRange.Count & " 個選択しました。", vbInformation
    Else
        MsgBox "背景色が設定されていないセルは見つかりませんでした。", vbInformation
    End If
End Sub