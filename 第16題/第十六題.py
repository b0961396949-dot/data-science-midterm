# ================================================================
# 第 16 題｜Agoda 台中飯店搜尋
# 使用技術：Selenium 開啟含城市參數的搜尋網址，BeautifulSoup 解析飯店卡片。
# 流程說明：載入搜尋頁 → 找飯店名稱與價格 → 整理成 agoda_result.csv。
# 輸出內容：飯店名、價格；找不到價格時標示未顯示。
# 報告提醒：目前使用搜尋網址，沒有自動在欄位輸入台中或設定入住日期；僅擷取已載入卡片。
# ================================================================

"""Agoda 搜尋台中並擷取結果頁可見的飯店名稱、價格。"""
import csv
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

OUT = Path(__file__).resolve().parent / "agoda_result.csv"
# city 與 text 是搜尋參數；quote 將中文轉成網址編碼，本程式沒有操作日期選單。
URL = "https://www.agoda.com/zh-tw/search?city=17269&text=" + quote("台中")


def main():
    driver = webdriver.Chrome()
    try:
        driver.get(URL)
        # 等到飯店元素或網址含 captcha 才繼續；這只是驗證頁的初步偵測。
        WebDriverWait(driver, 35).until(lambda d: d.find_elements("css selector", "[data-selenium='hotel-name'], [data-element-name='property-card']") or "captcha" in d.current_url.lower())
        if "captcha" in driver.current_url.lower():
            raise RuntimeError("Agoda 要求驗證；未嘗試繞過")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        # 兩種 CSS 選擇器用逗號連接，匹配不同版型的飯店卡片。
        cards = soup.select("[data-element-name='property-card'], [data-selenium='hotel-item']")
        rows = []
        for card in cards:
            name_tag = card.select_one("[data-selenium='hotel-name'], h3")
            # 價格保留畫面文字，未換算幣別；顯示內容可能依日期、房型與登入狀態不同。
            price_tag = card.select_one("[data-selenium='display-price'], [data-element-name='price']")
            if name_tag:
                rows.append([name_tag.get_text(" ", strip=True), price_tag.get_text(" ", strip=True) if price_tag else "未顯示"])
        # 若連一筆飯店資料都沒有就停止，避免寫出只有表頭的結果。
        if not rows:
            raise RuntimeError("Agoda 結果頁未提供可辨識飯店資料；可能需選日期或網站已改版")
        # with 自動關檔；w 覆寫舊檔，newline 避免多餘換行，UTF-8 BOM 方便 Excel 辨識中文。
        with OUT.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(["飯店名", "價格"]); w.writerows(rows)
        print(f"完成：{len(rows)} 間飯店，已存至 {OUT}")
    finally:
        # finally 在成功或發生例外時都會執行，確保 Chrome 與 WebDriver 正常關閉。
        driver.quit()


# 直接執行此檔（含 Spyder 執行檔案）才呼叫 main；被其他程式 import 時不自動抓資料。
if __name__ == "__main__":
    main()
