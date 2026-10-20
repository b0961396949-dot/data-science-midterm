# ================================================================
# 第 8 題｜近期上映推薦電影
# 使用技術：requests 與 BeautifulSoup 擷取開眼近期上映頁的清單。
# 流程說明：下載頁面 → 選取每個電影項目 → 整理片名、上映資訊與網址 → 寫入 movies.csv。
# 輸出內容：片名、上映時間、網址。
# 報告提醒：上映時間欄保留 runtime 區塊完整文字，可能同時包含片長等資訊。
# ================================================================

"""擷取開眼電影網近期上映強片，存入 movies.csv。"""
import csv
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = "https://www.atmovies.com.tw/movie/next/"
OUT = Path(__file__).resolve().parent / "movies.csv"


def main():
    response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
    # 先檢查 HTTP 錯誤，再指定 UTF-8；分號表示同一行有兩個依序執行的語句。
    response.raise_for_status(); response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    # 近期上映清單使用 filmListAllX/li；本週新片頁才使用 article.filmList。
    # CSS 的 > 表示直接子元素，取得電影清單下每個 li 項目。
    items = soup.select("ul.filmListAllX > li")
    rows = []
    for item in items:
        a = item.select_one(".filmtitle a")
        # 沒有片名連結或 href 的項目會跳過，避免輸出無效網址。
        if not a or not a.get("href"):
            continue
        # runtime 是網頁上的上映資訊容器；urljoin 將電影的相對連結補成完整網址。
        runtime = item.select_one(".runtime")
        rows.append([a.get_text(" ", strip=True), runtime.get_text(" ", strip=True) if runtime else "", urljoin(URL, a["href"])])
    if not rows:
        raise RuntimeError("頁面沒有符合的強片資料；網站版型可能已變更")
    # with 自動關檔；w 覆寫舊檔，newline 避免多餘換行，UTF-8 BOM 方便 Excel 辨識中文。
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["片名", "上映時間", "網址"]); w.writerows(rows)
    print(f"完成：{len(rows)} 部影片，已存至 {OUT}")


# 直接執行此檔（含 Spyder 執行檔案）才呼叫 main；被其他程式 import 時不自動抓資料。
if __name__ == "__main__":
    main()
