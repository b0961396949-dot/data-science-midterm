# ================================================================
# 第 10 題｜PTT 八卦板文章列表
# 使用技術：Selenium 操作頁面，BeautifulSoup 解析瀏覽器載入後的 HTML。
# 流程說明：開啟看板 → 處理年齡確認 → 找文章項目 → 輸出網站標題與 gossiping.csv。
# 輸出內容：網址、標題、作者；沒有文章連結的項目會跳過。
# 報告提醒：只讀目前列表頁，沒有逐篇進入文章，也沒有往前翻頁。
# ================================================================

"""以 Selenium 開啟 PTT 八卦板，若有年齡確認頁則按下確認後擷取列表。"""
import csv
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://www.ptt.cc/bbs/Gossiping/index.html"
OUT = Path(__file__).resolve().parent / "gossiping.csv"


def main():
    driver = webdriver.Chrome()
    try:
        driver.get(URL)
        wait = WebDriverWait(driver, 15)
        # 搜尋可能的年齡確認按鈕，以可見文字判斷後點擊；頁面文字改變時需調整。
        buttons = driver.find_elements(By.CSS_SELECTOR, ".over18 button, a.btn, button")
        if buttons:
            for button in buttons:
                if button.is_displayed() and ("我同意" in button.text or "進入" in button.text):
                    button.click(); break
        # 目前任一條件成立就繼續：有文章列，或網頁標題含批踢踢；後者不保證文章已載完。
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".r-ent") or "批踢踢" in d.title)
        # page_source 是瀏覽器當下的 HTML，讓 BeautifulSoup 處理之後的資料解析。
        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = []
        # .r-ent 是文章列表項目；.title a 提供標題和連結，.author 提供作者。
        for item in soup.select(".r-ent"):
            a = item.select_one(".title a")
            # 已刪除文章等項目可能沒有 a 標籤，直接跳過。
            if not a:
                continue
            author = item.select_one(".author")
            rows.append([urljoin(URL, a.get("href", "")), a.get_text(" ", strip=True), author.get_text(strip=True) if author else ""])
        if not rows:
            raise RuntimeError("沒有抓到文章；可能遇到 PTT 驗證、維護或版型更新")
        # with 自動關檔；w 覆寫舊檔，newline 避免多餘換行，UTF-8 BOM 方便 Excel 辨識中文。
        with OUT.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(["網址", "標題", "作者"]); w.writerows(rows)
        print(f"網站標題：{driver.title}\n完成：{len(rows)} 篇，已存至 {OUT}")
    finally:
        # finally 在成功或發生例外時都會執行，確保 Chrome 與 WebDriver 正常關閉。
        driver.quit()


# 直接執行此檔（含 Spyder 執行檔案）才呼叫 main；被其他程式 import 時不自動抓資料。
if __name__ == "__main__":
    main()
