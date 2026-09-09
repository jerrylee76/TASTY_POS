# Python 點餐收銀系統

## 執行

```powershell
python restaurant_pos.py
```

需要 Python 3.9 以上；使用標準 Tkinter，不需要安裝第三方套件。

## 已包含功能

- 點餐菜單、分類、數量增減、清空訂單；菜單由同目錄的 `menu.json` 匯入，支援條碼點餐
- 菜單編輯視窗：可新增、修改、刪除分類、名稱、價格、條碼與圖片路徑，儲存後寫回 `menu.json`
- Receipt Layout：可自訂收據抬頭、寬度，以及是否顯示稅額／小費
- 中英文一鍵切換（`中 / EN` 或 `Ctrl+L`）
- 稅率設定、TWD/USD/HKD/JPY 外幣結算與匯率設定
- AA 制分單
- 小費比例與小費統計
- 收據抬頭、寬度與儲存格式設定；收據會輸出為 `work/pos_data/receipt_latest.txt`
- 引導提示、快捷鍵：`F2` 設定、`F4` 清空、`F9` 結帳、`Ctrl+P` 收據
- 當日訂單數、營業額、小費總額統計
- 歷史訂單查詢與刪除保護；刪除需密碼及二次確認，密碼可於系統設定修改（預設 `1234`）
- 訂單資料與系統設定自動保存至 `work/pos_data/`

## 後續可擴充

目前「列印」先輸出 UTF-8 純文字收據，適合先驗證流程；接入實體熱敏印表機時，可把 `print_receipt()` 改接 Windows 印表機或 ESC/POS 驅動。修改 `menu.json` 後重新啟動程式即可載入新菜單。`category`、`name` 支援 `{ "zh": "中文", "en": "English" }`，另可加入 `barcode` 與 `image` 指向同目錄下的 PNG/GIF 圖片；圖片不存在時會自動退回文字顯示。
