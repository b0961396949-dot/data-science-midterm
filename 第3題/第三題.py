# ================================================================
# 第 3 題｜腸病毒就診人次資料下載
# 使用技術：requests 下載疾管署提供的 CSV；truststore 啟用作業系統的憑證驗證。
# 流程說明：設定 HTTPS 信任庫 → 下載官方 CSV → 檢查 HTTP 狀態 → 寫入本機檔案。
# 輸出內容：NHI_EnteroviralInfection.csv；保留來源的欄位與資料內容。
# 報告提醒：這題直接下載資料檔，不需要 BeautifulSoup；Spyder 使用的環境需有 truststore。
# ================================================================

# truststore 是額外套件，必須安裝在 Spyder 實際使用的 Python 環境。
import truststore

# 使用 macOS 系統憑證庫驗證 HTTPS。疾管署網站的 TWCA 憑證鏈
# 曾在本專案的 certifi 環境驗證失敗，因此改用系統信任庫，仍保留 HTTPS 驗證。
truststore.inject_into_ssl()

import requests
from pathlib import Path

# 目標下載網址
url = "https://od.cdc.gov.tw/eic/NHI_EnteroviralInfection.csv"

# 把檔案存到程式所在的資料夾，避免執行位置不同時導致輸出不在同一處
output_dir = Path(__file__).resolve().parent
filename = output_dir / "NHI_EnteroviralInfection.csv"

print("正在從政府開放資料平臺下載腸病毒就診人次統計資料...")

try:
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=60,
    )
    # 收到回應後檢查 HTTP 狀態；這一步檢查連線結果，並不驗證 CSV 的欄位內容。
    response.raise_for_status()
    # 以 UTF-8 解碼，utf-8-sig 也能處理來源檔案開頭可能帶有的 BOM 標記。
    response.encoding = "utf-8-sig"

    # with 會自動關檔；w 表示覆寫，utf-8-sig 讓 Excel 較容易辨識中文編碼。
    with open(filename, mode="w", encoding="utf-8-sig", newline="") as file:
        file.write(response.text)

    print(f"下載成功！資料已成功存入本地檔案：{filename.name}")
# 連線失敗、逾時、TLS 驗證或 HTTP 錯誤會在此印出原因。
except requests.exceptions.RequestException as e:
    print(f"下載失敗：{e}")
