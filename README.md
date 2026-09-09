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
- 歷史訂單可依單號及日、週、月、季、年篩選
- 訂單資料與系統設定自動保存至 `work/pos_data/`
- 主程式啟動自動最大化且禁止調整大小；關閉程式需輸入離開密碼
- 主程式使用 POS 固定全螢幕模式，不提供最小化／最大化／調整大小；菜單字型與大小可在系統設定修改

## 後續可擴充

目前「列印」先輸出 UTF-8 純文字收據，適合先驗證流程；接入實體熱敏印表機時，可把 `print_receipt()` 改接 Windows 印表機或 ESC/POS 驅動。修改 `menu.json` 後重新啟動程式即可載入新菜單。`category`、`name` 支援 `{ "zh": "中文", "en": "English" }`，另可加入 `barcode` 與 `image` 指向同目錄下的 PNG/GIF 圖片；圖片不存在時會自動退回文字顯示。

## 全新 Windows 電腦設定

1. 從 [Python 官方下載頁](https://www.python.org/downloads/windows/) 安裝 Python 3.11 或更新版本，安裝時勾選 `Add Python.exe to PATH`。
2. 開啟 PowerShell，測試 Python 與 Tkinter：

```powershell
python --version
python -m tkinter
```

如果出現 Tkinter 測試視窗，即表示環境正常。本系統只使用 Python 標準函式庫，不需要安裝第三方套件。

3. 複製完整資料夾，至少包含 `restaurant_pos.py`、`menu.json`、`images` 與 `work`。`work\pos_data` 內含系統設定、歷史訂單和收據資料；要保留資料時不可漏掉此資料夾。
4. 在 PowerShell 啟動：

```powershell
cd "C:\你的路徑\TASTY_POS"
python restaurant_pos.py
```

5. 菜單圖片須放在 `images` 資料夾，並在 `menu.json` 使用正確的相對路徑，例如 `"image": "images/ribs_rice.png"`。圖片支援 PNG/GIF；圖片不存在時會顯示文字菜單。
6. 第一次使用的離開／歷史訂單刪除密碼是 `1234`，請登入後到「系統設定 → 安全性」修改。
