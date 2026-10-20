# ================================================================
# 第 14 題｜NBA 球員薪資
# 使用技術：Selenium 載入 Hoopshype，BeautifulSoup 將第一個表格轉為資料列。
# 流程說明：等待表格 → 讀取欄名與資料 → 保存 all_play.csv → 另存前三列至 highest.csv。
# 輸出內容：all_play.csv 保留表格欄位；highest.csv 包含名字、背號、薪資。
# 報告提醒：前三名依來源排列，未自行排序；背號標示來源未提供；沒有處理額外分頁。
# ================================================================

"""用 Selenium 載入 Hoopshype 薪資頁，再以 BeautifulSoup 匯出前 3 名及全表。"""
import csv
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://hoopshype.com/salaries/players/"
OUT_DIR = Path(__file__).resolve().parent


def main():
    driver = webdriver.Chrome()
    try:
        driver.get(URL)
        # 等到表格有資料列再交給 BeautifulSoup 解析，避免只抓到初始空表格。
        WebDriverWait(driver, 25).until(lambda d: d.find_elements("css selector", "table tbody tr"))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        # select_one 只取頁面第一個 table；網站新增其他表格時，需要重新確認這個定位。
        table = soup.select_one("table")
        if not table:
            raise RuntimeError("找不到薪資表格")
        rows = []
        for tr in table.select("tbody tr"):
            # 把每個 td 的文字整理成列表，一個內層列表代表一位球員的表格資料列。
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if cells:
                rows.append(cells)
        if not rows:
            raise RuntimeError("薪資表沒有資料列")
        # 優先讀取 thead 的欄名；找不到表頭時，以欄位1、欄位2等暫代。
        headers = [th.get_text(" ", strip=True) for th in table.select("thead th")]
        if not headers:
            headers = [f"欄位{i+1}" for i in range(max(map(len, rows)))]
        # with 自動關檔；w 覆寫舊檔，newline 避免多餘換行，UTF-8 BOM 方便 Excel 辨識中文。
        with (OUT_DIR / "all_play.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(headers); w.writerows(rows)
        # Hoopshype 的薪資表沒有球衣背號欄；另輸出作業要求的基本欄位並如實標示未提供。
        # with 自動關檔；w 覆寫舊檔，newline 避免多餘換行，UTF-8 BOM 方便 Excel 辨識中文。
        with (OUT_DIR / "highest.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(["名字", "背號", "薪資"])
            # 假設第一個非空且不是 Player 的表頭就是薪資年度；欄位順序改變時可能需要調整。
            salary_index = next((i for i, h in enumerate(headers) if h and h != "Player"), None)
            # 列表切片取來源的前三列，假設來源已依薪資排序；程式沒有自行比較金額。
            for row in rows[:3]:
                name = row[1] if len(row) > 1 else ""
                salary = row[salary_index] if salary_index is not None and len(row) > salary_index else ""
                w.writerow([name, "來源未提供", salary])
        print(f"完成：全表 {len(rows)} 筆；前 3 名另存 highest.csv。背號欄是來源網站未提供。")
    finally:
        # finally 在成功或發生例外時都會執行，確保 Chrome 與 WebDriver 正常關閉。
        driver.quit()


# 直接執行此檔（含 Spyder 執行檔案）才呼叫 main；被其他程式 import 時不自動抓資料。
if __name__ == "__main__":
    main()
