# ================================================================
# 第 4 題｜博客來搜尋「演算法」
# 使用技術：requests 優先下載；失敗時使用 Selenium 載入一般 Chrome。
# 資料解析：BeautifulSoup 讀取第一頁的書籍卡片，csv 負責輸出。
# 流程說明：搜尋 → 等待書籍資料 → 擷取四個欄位 → 驗證後寫入 booklist.csv。
# 輸出內容：書名、網址、作者、書價；不會自動翻到下一頁。
# 報告提醒：作者欄保留搜尋頁列出的相關人員，可能包含譯者；書價取頁面售價。
# 若改用 Chrome，報告時需說明使用了 Selenium 與 BeautifulSoup。
# ================================================================

import csv
import re
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

KEYWORD = "演算法"
# quote 將中文轉成可放入網址路徑的編碼。
URL = f"https://search.books.com.tw/search/query/key/{quote(KEYWORD)}/cat/all"
OUTPUT_FILE = Path(__file__).resolve().parent / "booklist.csv"
# 正文卡片與底部功能列的 id 都有這個前綴，解析時還要核對商品編號。
CARD_SELECTOR = '[id^="prod-itemlist-"]'


def parse_books(html):
    """解析目前搜尋頁的書籍卡片，排除導覽列、底部按鈕及重複商品。"""
    soup = BeautifulSoup(html, "html.parser")
    rows, seen = [], set()
    for card in soup.select(CARD_SELECTOR):
        # 完整匹配商品 id，排除 prod-itemlist-footer-... 這類底部功能列。
        match = re.fullmatch(r"prod-itemlist-(\d+)", card.get("id", ""))
        if not match:
            continue
        product_id = match.group(1)
        if product_id in seen:
            continue

        # 搜尋所有商品的頁面也可能出現非書籍商品，只保留書籍類型。
        category = card.select_one(".type > p")
        if category is None or "書" not in category.get_text(strip=True):
            continue
        # 現行版型用 h4，並非舊程式假設的 h3。
        title_tag = card.select_one("h4 a[href]")
        if title_tag is None:
            raise ValueError(f"商品 {product_id} 缺少書名或網址，請檢查頁面版型")
        # 優先取 title 屬性，以免關鍵字的 em 標籤在書名中產生多餘空格。
        title = (title_tag.get("title") or title_tag.get_text("", strip=True)).strip()
        link = urljoin(URL, title_tag["href"])
        parsed = urlparse(link)
        host = (parsed.hostname or "").lower()
        if not title or parsed.scheme != "https" or not (
            host == "books.com.tw" or host.endswith(".books.com.tw")
        ):
            raise ValueError(f"商品 {product_id} 的書名或博客來連結無效")

        # 搜尋頁的 author 區塊可能同時列出作者與譯者，保留來源列出的姓名。
        author_tag = card.select_one(".author")
        author = author_tag.get_text("、", strip=True) if author_tag else "來源未提供"
        # 例：優惠價 79 折、316 元；必須取「元」前的金額，不能誤取折扣 79。
        price_tag = card.select_one(".price")
        price_text = price_tag.get_text(" ", strip=True) if price_tag else ""
        amounts = re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*元", price_text)
        if not amounts:
            raise ValueError(f"《{title}》尚未載入可辨識的售價，沒有更新 CSV")
        price = amounts[-1].replace(",", "") + " 元"
        rows.append([title, link, author or "來源未提供", price])
        seen.add(product_id)

    if not rows:
        raise ValueError("頁面沒有可辨識的書籍資料，可能仍在驗證或網站版型改變")
    return rows


def fetch_books():
    """先用 requests；HTTP 403 或缺少書籍資料時，改以可見的 Chrome 載入。"""
    try:
        print("[1/4] 正在連線到博客來……")
        response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        print(f"HTTP 狀態：{response.status_code}")
        response.raise_for_status()
        response.encoding = "utf-8"
        rows = parse_books(response.text)
        print("取得方式：requests + BeautifulSoup")
        return rows
    except (requests.RequestException, ValueError) as error:
        print(f"直接下載未取得可用資料：{error}")
        print("[2/4] 正在開啟 Chrome，等待博客來搜尋結果……")

    driver = webdriver.Chrome()
    try:
        driver.set_page_load_timeout(40)
        driver.get(URL)

        def loaded_books(browser):
            # 每次檢查實際資料是否可解析，避免只看到搜尋框就誤以為載入完成。
            try:
                return parse_books(browser.page_source)
            except ValueError:
                return False

        rows = WebDriverWait(driver, 30).until(loaded_books)
        print("取得方式：Selenium Chrome + BeautifulSoup")
        return rows
    except TimeoutException as error:
        raise ValueError("Chrome 未能及時取得完整的書籍欄位，請確認網頁或稍後再試") from error
    finally:
        # 不論成功或發生例外，都關閉此次建立的 Chrome 和 WebDriver。
        driver.quit()


def save_books(rows):
    """先完成暫存檔，再替換正式 CSV，避免下載失敗或寫到一半就清空舊資料。"""
    temporary = OUTPUT_FILE.with_suffix(".csv.tmp")
    try:
        # UTF-8 BOM 方便 Excel 辨識中文，newline 避免額外空白列。
        with temporary.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["書名", "網址", "作者", "書價"])
            writer.writerows(rows)
        temporary.replace(OUTPUT_FILE)
    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    print(f"正在搜尋博客來關鍵字：{KEYWORD} ...")
    try:
        rows = fetch_books()
    except (requests.RequestException, ValueError, WebDriverException) as error:
        print(f"本次抓取未完成：{error}")
        print("沒有更新 booklist.csv；已有檔案仍是先前資料。")
        return

    print(f"[3/4] 第一頁取得 {len(rows)} 筆書籍，準備儲存……")
    try:
        save_books(rows)
    except OSError as error:
        print(f"書籍資料已取得，但存檔失敗：{error}")
        return
    for index, (title, link, author, price) in enumerate(rows, start=1):
        print(f"{index}. {title} | {author} | {price}")
    print(f"[4/4] 完成！{len(rows)} 筆書籍已存至：{OUTPUT_FILE}")


# 在 Spyder 執行檔案會呼叫 main；import 時不會自動下載或開啟 Chrome。
if __name__ == "__main__":
    main()
