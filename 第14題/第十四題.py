# ================================================================
# 第 14 題｜NBA 球員薪資
# 使用技術：Selenium 載入 Hoopshype，BeautifulSoup 將第一個表格轉為資料列。
# 流程說明：等待表格 → 讀取欄名與資料 → 保存 all_play.csv → 另存前三列至 highest.csv。
# 輸出內容：all_play.csv 保留表格欄位；highest.csv 包含名字、背號、薪資。
# 報告提醒：依第一個薪資年度欄的數值選出前三名；背號標示來源未提供，沒有處理額外分頁。
# ================================================================

"""用 Selenium 載入 Hoopshype 薪資頁，再以 BeautifulSoup 匯出前 3 名及全表。"""
import csv
from pathlib import Path
import re
from decimal import Decimal

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://hoopshype.com/salaries/players/"
OUT_DIR = Path(__file__).resolve().parent


def parse_salary_table(html):
    """依 Player 與年度表頭找薪資表，不假設姓名、排名與薪資的固定欄位位置。"""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.select("table"):
        header_rows = table.select("thead tr")
        if not header_rows:
            continue
        headers = [cell.get_text(" ", strip=True) for cell in header_rows[-1].find_all(["th", "td"], recursive=False)]
        name_index = next((i for i, label in enumerate(headers) if label.casefold() in ("player", "player name", "球員", "姓名")), None)
        salary_index = next((i for i, label in enumerate(headers) if re.search(r"20\d{2}\s*[-–/]\s*(?:20)?\d{2}", label)), None)
        if name_index is None or salary_index is None:
            continue
        rows = []
        for tr in table.select("tbody tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"], recursive=False)]
            if not cells:
                continue
            if len(cells) != len(headers):
                raise ValueError("薪資資料與表頭欄數不一致，未更新 CSV")
            if cells[name_index]:
                rows.append(cells)
        if not rows:
            raise ValueError("薪資表沒有球員資料")
        return headers, rows, name_index, salary_index
    raise ValueError("找不到同時含 Player 與薪資年度表頭的表格，未更新 CSV")


def highest_three(rows, name_index, salary_index):
    """以金額排序，排除來源未提供薪資的列；排名不能當作薪資。"""
    ranked = []
    for row in rows:
        match = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", row[salary_index])
        if match:
            amount = Decimal(match.group(1).replace(",", ""))
            ranked.append((amount, row))
    if len(ranked) < 3:
        raise ValueError("可辨識薪資不足三位球員，未更新 CSV")
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [[row[name_index], "來源未提供", row[salary_index]] for _, row in ranked[:3]]


def main():
    driver = webdriver.Chrome()
    try:
        driver.get(URL)
        # 等到表格有資料列再交給 BeautifulSoup 解析，避免只抓到初始空表格。
        WebDriverWait(driver, 25).until(lambda d: d.find_elements("css selector", "table tbody tr"))
        headers, rows, name_index, salary_index = parse_salary_table(driver.page_source)
        # 在開啟輸出檔前完成欄位檢查與前三名計算，避免錯誤資料覆蓋舊成果。
        top_three = highest_three(rows, name_index, salary_index)
        # with 自動關檔；w 覆寫舊檔，newline 避免多餘換行，UTF-8 BOM 方便 Excel 辨識中文。
        with (OUT_DIR / "all_play.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(headers); w.writerows(rows)
        # Hoopshype 的薪資表沒有球衣背號欄；另輸出作業要求的基本欄位並如實標示未提供。
        # with 自動關檔；w 覆寫舊檔，newline 避免多餘換行，UTF-8 BOM 方便 Excel 辨識中文。
        with (OUT_DIR / "highest.csv").open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(["名字", "背號", "薪資"])
            w.writerows(top_three)
        print(f"完成：全表 {len(rows)} 筆；前 3 名另存 highest.csv。背號欄是來源網站未提供。")
    finally:
        # finally 在成功或發生例外時都會執行，確保 Chrome 與 WebDriver 正常關閉。
        driver.quit()


# 直接執行此檔（含 Spyder 執行檔案）才呼叫 main；被其他程式 import 時不自動抓資料。
if __name__ == "__main__":
    main()
