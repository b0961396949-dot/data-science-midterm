import os
# ================================================================
# 第 7 題｜Google Books API 分頁查詢
# 使用技術：requests 發送 GET，解析 JSON，csv 輸出書籍資料。
# 流程說明：查詢 startIndex=0、10 → 整理 volumeInfo → 合併後寫入檔案。
# 輸出內容：頁次、書名、作者、出版社、出版日期、網址。
# 報告提醒：projection=lite 只取精簡資料，部分欄位可能沒有值。
# 每頁最多 10 筆、兩頁最多 20 筆；API 實際回傳數量可能較少。
# 若遇到配額限制，需使用已啟用 Books API 且有可用配額的 Google 專案 Key。
# 在下方 API_KEY 的雙引號內貼上自己的 Google Books API 金鑰。
# ================================================================

import csv
import re
from pathlib import Path
from urllib.parse import quote, quote_plus

import requests

# =============================
# API 金鑰設定：把完整金鑰貼在雙引號內，再儲存並執行。
# =============================
API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY", "")

URL = "https://www.googleapis.com/books/v1/volumes"
OUT = Path(__file__).resolve().parent / "pythonbook.csv"
FIELDS = ["頁次", "書名", "作者", "出版社", "出版日期", "網址"]


def api_error_hint(payload, api_key=""):
    """辨識錯誤原因；未知原因顯示遮蔽金鑰及網址後的 Google 訊息。"""
    error = payload.get("error")
    if not isinstance(error, dict):
        return ""
    reasons = set()
    # 新格式在 details 的 ErrorInfo；舊格式在 errors 的 reason。
    for field in ("details", "errors"):
        entries = error.get(field, [])
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and isinstance(entry.get("reason"), str):
                    reasons.add(entry["reason"])
    hints = {
        "API_KEY_INVALID": "API Key 無效：請從 Google Cloud 憑證頁複製完整的 API 金鑰值，確認不是金鑰名稱或 OAuth 用戶端 ID",
        "keyInvalid": "API Key 無效：請重新複製完整的 API 金鑰值",
        "SERVICE_DISABLED": "Key 所屬專案尚未啟用 Books API：請在同一專案啟用 Books API",
        "accessNotConfigured": "請在 Key 所屬專案啟用 Books API",
        "API_KEY_SERVICE_BLOCKED": "金鑰的 API 限制未允許 Books API：請將 Books API 加入允許清單",
        "API_KEY_HTTP_REFERRER_BLOCKED": "金鑰限制為網站來源，與 Spyder 的 Python 請求不符：請使用適合此程式的金鑰限制設定",
        "API_KEY_IP_ADDRESS_BLOCKED": "目前對外 IP 不在金鑰允許清單：請檢查 IP 限制",
        "API_KEY_ANDROID_APP_BLOCKED": "金鑰限制為 Android 應用程式，與 Spyder 的 Python 請求不符",
        "API_KEY_IOS_APP_BLOCKED": "金鑰限制為 iOS 應用程式，與 Spyder 的 Python 請求不符",
    }
    for reason, hint in hints.items():
        if reason in reasons:
            return f"{reason}：{hint}"
    # 部分回應只有文字訊息，沒有 ErrorInfo 的 reason。
    message = error.get("message", "")
    if isinstance(message, str) and "api key not valid" in message.lower():
        return hints["API_KEY_INVALID"]
    if isinstance(message, str) and "api keys are not supported by this api" in message.lower():
        return (
            "Google 拒絕此請求的金鑰認證；Books 公開搜尋支援 API Key。"
            "請先確認使用的是未綁定服務帳戶的標準 API 金鑰，"
            "並在同一專案啟用 Books API、讓金鑰的 API 限制允許 Books API。"
            "僅憑此訊息無法確認金鑰類型，請至 Google Cloud 憑證頁檢查"
        )
    if isinstance(message, str) and message.strip():
        # 遮蔽完整金鑰、網址編碼後的金鑰、Google 金鑰格式及網址。
        # 不輸出完整 JSON、請求網址或任何請求標頭。
        if api_key:
            for secret in (api_key, quote(api_key, safe=""), quote_plus(api_key)):
                message = message.replace(secret, "[金鑰已遮蔽]")
        message = re.sub(r"AIza[\w-]+", "[金鑰已遮蔽]", message)
        message = re.sub(r"https?://\S+", "[網址已遮蔽]", message)
        message = " ".join(message.split())[:500]
        return f"Google 錯誤訊息（已遮蔽金鑰）：{message}"
    return ""


def fetch_page(start, api_key=""):
    """取得一頁 JSON；把連線、API 及資料格式錯誤轉成報告時能理解的訊息。"""
    params = {"q": "Python", "maxResults": 10, "projection": "lite", "startIndex": start}
    if api_key:
        params["key"] = api_key
    try:
        response = requests.get(URL, params=params, timeout=25)
    except requests.RequestException as error:
        # 不印出原始例外網址，避免其中的 key 查詢參數出現在 Console 或截圖。
        raise ValueError(f"連線失敗（{type(error).__name__}），請確認網路與憑證設定") from None

    try:
        payload = response.json()
    except ValueError:
        raise ValueError(f"HTTP {response.status_code}：回應不是有效 JSON") from None
    if not isinstance(payload, dict):
        raise ValueError("API 回應格式異常：預期為 JSON 物件")

    # 429 可能是每日配額耗盡，也可能是目前使用的專案配額為 0，不能一律當短暫限流。
    if response.status_code == 429:
        error = payload.get("error")
        details = error.get("details", []) if isinstance(error, dict) else []
        if not isinstance(details, list):
            details = []
        zero_quota = any(
            isinstance(item, dict)
            and isinstance(item.get("metadata"), dict)
            and str(item["metadata"].get("quota_limit_value")) == "0"
            for item in details
        )
        reason = "此次請求所對應的配額上限為 0" if zero_quota else "此次請求超過可用配額或速率限制"
        advice = "請檢查 Key 所屬專案的 Books API 配額" if api_key else "請填入程式開頭的 API_KEY 並確認可用配額"
        raise ValueError(f"Google Books API 回應 429：{reason}；{advice}")
    if response.status_code in (400, 401, 403):
        hint = api_error_hint(payload, api_key)
        if not hint:
            hint = "Google 未提供可辨識的原因；請確認完整 API 金鑰值、同一專案的 Books API 啟用狀態及金鑰限制"
        raise ValueError(f"HTTP {response.status_code}：{hint}")
    if not response.ok or "error" in payload:
        raise ValueError(f"Google Books API 回應錯誤（HTTP {response.status_code}）")
    return payload


def parse_page(payload, page):
    """把一頁 JSON 整理成六欄；缺少可選欄位時保留空白，不自行補造資料。"""
    items = payload.get("items", [])
    if not isinstance(items, list):
        raise ValueError(f"第 {page} 頁的 items 不是列表")
    rows = []
    for book in items:
        if not isinstance(book, dict) or not isinstance(book.get("volumeInfo"), dict):
            raise ValueError(f"第 {page} 頁的書籍格式不符")
        info = book["volumeInfo"]
        if not info.get("title"):
            raise ValueError(f"第 {page} 頁含缺少書名的資料")
        # authors 為列表，以分號連接多位作者；get 處理 lite 投影未提供的欄位。
        rows.append([
            page, info["title"], "; ".join(info.get("authors") or []),
            info.get("publisher", ""), info.get("publishedDate", ""), info.get("infoLink", ""),
        ])
    return rows


def save_books(rows):
    """兩頁均完成後才存檔，先寫暫存檔再替換正式 CSV。"""
    temporary = OUT.with_suffix(".csv.tmp")
    try:
        # UTF-8 BOM 讓 Excel 容易辨識中文；newline 避免多餘的空白列。
        with temporary.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(FIELDS)
            writer.writerows(rows)
        temporary.replace(OUT)
    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    api_key = API_KEY.strip()
    print("Google Books API：搜尋 Python，取得前兩頁。")
    if not api_key:
        print('請先在程式開頭的 API_KEY = "" 填入完整金鑰，儲存後再執行。')
        return
    print("API Key：已讀取（尚未確認有效）")
    rows = []
    try:
        # 起始位置從 0 起算；第二頁從第 11 筆開始，因此 startIndex=10。
        for page, start in enumerate((0, 10), start=1):
            print(f"正在取得第 {page} 頁（startIndex={start}）……")
            page_rows = parse_page(fetch_page(start, api_key), page)
            print(f"第 {page} 頁：{len(page_rows)} 筆")
            rows.extend(page_rows)
        if not rows:
            raise ValueError("兩頁皆未回傳書籍資料")
        save_books(rows)
    except (ValueError, OSError) as error:
        print(f"本次未完成：{error}")
        print("尚未更新 pythonbook.csv；若已有檔案，其中是先前資料。")
        return
    print(f"完成：兩頁共 {len(rows)} 筆，已存至 {OUT}")


# Spyder 直接執行此檔時呼叫 main；import 時不自動發出 API 請求。
if __name__ == "__main__":
    main()
