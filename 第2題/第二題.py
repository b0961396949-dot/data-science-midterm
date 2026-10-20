# ================================================================
# 第 2 題｜臺灣銀行牌告匯率
# 使用技術：requests 優先下載；取不到表格時，以 Selenium 開啟一般 Chrome。
# 資料解析：BeautifulSoup 擷取幣別與四種匯率，csv 負責存檔。
# 流程說明：取得頁面 → 檢查表格與掛牌時間 → 整理資料 → 輸出 bank.csv。
# 輸出內容：時間、幣別、現金買入、現金賣出、即期買入、即期賣出。
# 報告提醒：時間取自臺銀掛牌時間；若改用瀏覽器，需說明有使用 Selenium。
# ================================================================

import csv
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

BANK_URL = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
OUTPUT_FILE = Path(__file__).resolve().parent / "bank.csv"
RATE_FIELDS = ["現金買入", "現金賣出", "即期買入", "即期賣出"]


def parse_bank_rates(html):
    """將官方網頁轉成掛牌時間與匯率列表；驗證頁或缺欄位時停止。"""
    soup = BeautifulSoup(html, "html.parser")
    # 精確指定牌告表，避免把網頁的其他表格或驗證提示當作匯率。
    table = soup.select_one('table[title="牌告匯率"]')
    if table is None:
        raise ValueError("沒有取得臺銀匯率表，頁面可能仍在驗證或版型已改變")

    # 取網站掛牌時間，不能用程式執行時間冒充資料更新時間。
    time_tag = soup.select_one("span.time")
    quoted_time = time_tag.get_text(" ", strip=True) if time_tag else ""
    if not re.fullmatch(r"\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}(?::\d{2})?", quoted_time):
        raise ValueError("找不到有效的掛牌時間")

    rows = []
    seen = set()
    for tr in table.select("tbody tr"):
        currency_cell = tr.select_one("td.currency")
        if currency_cell is None:
            continue
        # 原頁同時放了手機版與桌面版名稱，只取一份以免出現「美金 美金」。
        name_tag = currency_cell.select_one(".hidden-phone")
        if name_tag is None:
            name_tag = currency_cell.select_one(".visible-phone")
        if name_tag is None:
            name_tag = currency_cell
        currency = " ".join(name_tag.get_text(" ", strip=True).split())
        if not currency or currency in seen:
            raise ValueError("幣別名稱缺漏或重複，請檢查網站版型")

        record = {"幣別": currency}
        for field in RATE_FIELDS:
            # data-table 指出格子的用途，比單靠第幾欄更清楚。
            # select_one 取第一格，排除網頁中另外提供的列印版重複欄位。
            cell = tr.select_one(f'td[data-table="本行{field}"]')
            value = cell.get_text(strip=True) if cell else ""
            # 「-」代表來源未提供該種報價，必須保留，不能當成 0 元。
            if not re.fullmatch(r"(?:\d+(?:\.\d+)?|-)", value):
                raise ValueError(f"{currency} 的{field}資料缺漏或格式不符")
            record[field] = value
        seen.add(currency)
        rows.append(record)

    if not rows:
        raise ValueError("匯率表沒有資料列")
    return quoted_time, rows


def fetch_bank_rates():
    """先下載原始 HTML；失敗時改由一般 Chrome 載入同一官方網址。"""
    try:
        response = requests.get(
            BANK_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20
        )
        response.raise_for_status()
        response.encoding = "utf-8"
        quoted_time, rows = parse_bank_rates(response.text)
        print("取得方式：requests + BeautifulSoup")
        return quoted_time, rows
    except (requests.RequestException, ValueError) as error:
        print(f"直接下載尚未取得可用匯率：{error}")
        print("正在開啟 Chrome，等待臺銀匯率表載入……")

    # Selenium 啟動可見的 Chrome；不需要輸入網銀帳號或密碼。
    driver = webdriver.Chrome()
    try:
        driver.set_page_load_timeout(40)
        driver.get(BANK_URL)
        # 顯式等待表格有內容，最多等 30 秒；條件成立就繼續。
        WebDriverWait(driver, 30).until(
            lambda browser: browser.find_elements(
                "css selector", 'table[title="牌告匯率"] td.rate-content-cash'
            )
        )
        quoted_time, rows = parse_bank_rates(driver.page_source)
        print("取得方式：Selenium Chrome + BeautifulSoup")
        return quoted_time, rows
    except TimeoutException as error:
        raise ValueError("Chrome 未能及時載入匯率表，請確認頁面或稍後再試") from error
    finally:
        # 成功或失敗都會關閉此次開啟的 Chrome，不留下背景程序。
        driver.quit()


def save_bank_rates(quoted_time, rows):
    """先寫暫存檔，全部寫完才替換 bank.csv，避免留下寫到一半的檔案。"""
    temporary = OUTPUT_FILE.with_suffix(".csv.tmp")
    try:
        # UTF-8 BOM 方便 Excel 辨識中文；newline 避免 CSV 出現多餘空白列。
        with temporary.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["時間", "幣別", *RATE_FIELDS])
            for row in rows:
                writer.writerow([quoted_time, row["幣別"], *[row[f] for f in RATE_FIELDS]])
        temporary.replace(OUTPUT_FILE)
    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    print(f"執行時間：{datetime.now():%Y/%m/%d %H:%M}")
    try:
        quoted_time, rows = fetch_bank_rates()
    except (requests.RequestException, ValueError, WebDriverException) as error:
        print(f"本次未取得匯率：{error}")
        print("尚未更新 bank.csv；若已有檔案，其中是先前資料。")
        return

    try:
        save_bank_rates(quoted_time, rows)
    except OSError as error:
        print(f"匯率已取得，但檔案儲存失敗：{error}")
        return

    print("資料來源：臺灣銀行牌告匯率")
    print(f"牌價掛牌時間：{quoted_time}")
    for row in rows:
        values = " | ".join(f"{field}：{row[field]}" for field in RATE_FIELDS)
        print(f"{row['幣別']} | {values}")
    print(f"完成！已儲存 {len(rows)} 筆幣別資料至：{OUTPUT_FILE}")


# 在 Spyder 執行檔案會呼叫 main；其他程式 import 本檔時不會自動開啟瀏覽器。
if __name__ == "__main__":
    main()
