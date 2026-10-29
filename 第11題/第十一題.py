# ================================================================
# 第 11 題｜NBA 商品分頁存檔
# 使用技術：requests 取得教學頁原始碼，re 定位 tableData，json 解析其中的商品陣列。
# 流程說明：取得內嵌資料 → 每 10 筆切成一組 → 分別輸出 NBA_Products1.csv 等檔案。
# 輸出內容：商品編號、商品名稱、價格；每存一頁就在 Console 印出頁碼。
# 報告提醒：程式在本機將資料分頁，沒有用瀏覽器逐頁點擊；分頁大小固定為 10。
# ================================================================

"""逐頁擷取 NBA 商品並分頁輸出 NBA_Products1..n.csv。"""
import csv
import json
from pathlib import Path
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

START = "https://fchart.github.io/ML/nba_items.html"
OUT_DIR = Path(__file__).resolve().parent


def main():
    # Session 可共用連線設定與標頭；seen 集合用來避免重複處理同一網址。
    session = requests.Session(); session.headers.update({"User-Agent": "Mozilla/5.0"})
    url = START; seen = set(); page = 0
    while url and url not in seen:
        seen.add(url)
        response = session.get(url, timeout=25); response.raise_for_status(); response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        # 此教學頁用 JavaScript tableData 分頁，HTTP 原始表格只有欄名；
        # 直接解析同一頁內嵌的資料陣列，按網頁每頁 10 筆的規則輸出。
        # 正規表示式只定位變數宣告的結尾，後面的 JSON 交給專用解析器處理。
        match = re.search(r"var\s+tableData\s*=\s*", response.text)
        if not match:
            raise RuntimeError("找不到網頁內嵌的商品資料 tableData")
        # raw_decode 從 match.end() 開始讀一個 JSON 值；回傳的下一個位置在此不使用。
        # 因此陣列後面即使還有其他 JavaScript，也不需要當成 JSON 解析。
        products, _ = json.JSONDecoder().raw_decode(response.text, match.end())
        if not isinstance(products, list) or not products or not all(isinstance(p, dict) for p in products):
            raise RuntimeError("商品資料必須是非空的 JSON 物件列表")
        # 切片 products[start:start + 10] 每次取最多 10 筆，最後不足 10 筆也會保存。
        for start in range(0, len(products), 10):
            page += 1
            target = OUT_DIR / f"NBA_Products{page}.csv"
            # with 自動關檔；w 覆寫舊檔，newline 避免多餘換行，UTF-8 BOM 方便 Excel 辨識中文。
            with target.open("w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f); w.writerow(["商品編號", "商品名稱", "價格"])
                w.writerows([[p.get("id", ""), p.get("title", ""), p.get("price", "")] for p in products[start:start + 10]])
            for product in products[start:start + 10]:
                print(f"{product.get('id', '')}｜{product.get('title', '')}｜{product.get('price', '')}")
            print(f"儲存頁面: {page}（{min(10, len(products) - start)} 筆）")
        # 這一頁已內嵌全部商品資料；清空 url 讓外層迴圈結束，沒有另外請求分頁網址。
        url = ""
    if not page:
        raise RuntimeError("沒有取得任何商品頁")


# 直接執行此檔（含 Spyder 執行檔案）才呼叫 main；被其他程式 import 時不自動抓資料。
if __name__ == "__main__":
    main()
