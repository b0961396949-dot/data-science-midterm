# 資料科學期中考

第 1～17 題 Python 程式、既有輸出檔與題目 PDF。此儲存庫僅收錄期中考資料。

## 檔案配置

- `第1題/` 至 `第17題/`：各題程式及既有 CSV、HTML 或截圖成果。
- `資料科學期中報告題型.pdf`：題目說明。
- `requirements.txt`：Python 套件需求。
- `.env.example`：本機需設定的環境變數名稱，沒有憑證。

## 執行

建議使用 Python 3.12 與 Chrome。

```bash
python -m pip install -r requirements.txt
python "第1題/第一題.py"
```

也可在已安裝套件的 Spyder 環境開啟個別程式執行。
Selenium 題目會開啟瀏覽器，需可用的 Chrome 與網路。

## 本機憑證

第 7 題使用 `GOOGLE_BOOKS_API_KEY`。
第 17 題使用 `GITHUB_USERNAME`、`GITHUB_PASSWORD`，或沿用執行後在本機建立的獨立瀏覽器登入狀態。
請先在啟動 Python 或 Spyder 的環境設定這些環境變數。
程式不會自動載入 `.env`；`.env.example` 只供查看變數名稱。
金鑰、密碼、瀏覽器設定檔、GitHub 登入後的首頁與個人區塊截圖均未上傳。

## 驗證與限制

上傳前已檢查全部 17 個 Python 程式的語法。
本次未重新執行各題的網路查詢；隨附成果是原資料夾的既有檔案。
網站改版、Google 驗證、API 授權及額度、登入狀態都可能影響實際執行。
第 15 題遇到 Google 驗證時可等待使用者手動完成，完成後再繼續。
未附成果檔的題目不代表已完成網路擷取。
