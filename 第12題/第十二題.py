# ================================================================
# 第 12 題｜Google 搜尋 Steam 遊戲推薦
# 使用技術：Selenium 開啟帶有搜尋參數的 Google 網址，擷取可見的外部連結。
# 流程說明：網址編碼 → 等待結果或驗證頁 → 篩選與去重 → 保存 CSV 和截圖。
# 輸出內容：steam_game_recommendations.csv：搜尋關鍵字、結果標題、超連結；另存 google_search.png。
# 報告提醒：搜尋是透過網址參數送出；連結篩選不保證每一筆都是一般自然搜尋結果。
# 全程不要求手動操作；若 Google 阻擋，保存畫面並回報未完成，保留既有 CSV。
# ================================================================

"""使用 Selenium 搜尋 Google「Steam 遊戲推薦」並保存結果。"""

import csv
from pathlib import Path
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


QUERY = "Steam 遊戲推薦"
# quote_plus 處理中文與空格，將搜尋關鍵字放進 q 查詢參數。
URL = "https://www.google.com/search?q=" + quote_plus(QUERY)
OUTPUT_DIR = Path(__file__).resolve().parent
CSV_FILE = OUTPUT_DIR / "steam_game_recommendations.csv"
SCREENSHOT_FILE = OUTPUT_DIR / "google_search.png"
VERIFY_SCREENSHOT_FILE = OUTPUT_DIR / "google_verification.png"


def search_results_ready(browser):
    """等待可見的結果標題；驗證頁的容器不能當成搜尋成功。"""
    if "/sorry/" in browser.current_url:
        return False
    try:
        return any(
            heading.is_displayed()
            for heading in browser.find_elements(By.CSS_SELECTOR, "#search a h3, #rso a h3")
        )
    except StaleElementReferenceException:
        # 頁面正在切換，下次輪詢再檢查。
        return False


def wait_for_results(driver):
    """自動等待搜尋結果；遇到驗證或無結果時回報失敗。"""
    try:
        WebDriverWait(driver, 20).until(
            lambda browser: "/sorry/" in browser.current_url or search_results_ready(browser)
        )
    except TimeoutException:
        # 等待結束後統一保存未完成的頁面畫面。
        pass
    if search_results_ready(driver):
        return
    driver.save_screenshot(str(VERIFY_SCREENSHOT_FILE))
    if "/sorry/" in driver.current_url:
        raise ValueError("Google 回傳流量驗證頁，本次未取得搜尋結果；既有 CSV 保留。")
    raise ValueError("Google 未在等待時間內顯示可讀取的搜尋結果；既有 CSV 保留。")


def main():
    # 預設顯示 Chrome 視窗，符合題目使用 Selenium 與 WebDriver 的要求。
    driver = None
    try:
        print(f"正在開啟 Chrome，搜尋「{QUERY}」……", flush=True)
        driver = webdriver.Chrome()
        driver.set_page_load_timeout(45)
        driver.get(URL)
        wait_for_results(driver)

        results = []
        seen_urls = set()
        # 只讀取 #cnt 範圍內帶 href 的連結，並排除瀏覽器中未顯示的元素。
        for link in driver.find_elements(By.CSS_SELECTOR, "#cnt a[href]"):
            if not link.is_displayed():
                continue
            # 優先取無障礙標籤 aria-label，沒有時才用連結的可見文字。
            title = (link.get_attribute("aria-label") or link.text).strip()
            href = link.get_attribute("href")
            if not title or not href or not href.startswith(("http://", "https://")):
                continue
            # 這是網址字串篩選，排除部分 Google 內部連結；並非完整的網域驗證。
            if "google.com/" in href or "googleusercontent.com/" in href:
                continue
            # 用集合檢查是否已見過同一網址，避免重複輸出。
            if href in seen_urls:
                continue
            seen_urls.add(href)
            results.append([title, href])

        if not results:
            print("頁面沒有可辨識的外部搜尋結果；未更新 CSV。")
            return

        # with 自動關檔；w 覆寫舊檔，newline 避免多餘換行，UTF-8 BOM 方便 Excel 辨識中文。
        temporary = CSV_FILE.with_suffix(".csv.tmp")
        with temporary.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["搜尋關鍵字", "結果標題", "超連結"])
            writer.writerows([[QUERY, title, href] for title, href in results])
        temporary.replace(CSV_FILE)

        for title, href in results:
            print(f"{title}\n{href}\n")
        driver.save_screenshot(str(SCREENSHOT_FILE))
        print(f"搜尋「{QUERY}」找到 {len(results)} 筆結果，已存入：{CSV_FILE}")
        print(f"頁面截圖已存入：{SCREENSHOT_FILE}")
    except ValueError as error:
        print(f"本次未完成：{error}")
        print(f"未完成的頁面截圖：{VERIFY_SCREENSHOT_FILE}")
    except TimeoutException:
        print("等待逾時，本次未完成搜尋；尚未更新 CSV，既有資料保留。")
    except WebDriverException:
        print("Chrome 連線或操作中斷，本次未完成；請確認視窗沒有被關閉，再重新執行。")
    except OSError:
        print("檔案寫入失敗；請檢查資料夾權限，以及 CSV 是否被其他程式鎖定。")
    finally:
        # finally 在成功或發生例外時都會執行，確保 Chrome 與 WebDriver 正常關閉。
        if driver is not None:
            try:
                driver.quit()
            except WebDriverException:
                pass


# 直接執行此檔（含 Spyder 執行檔案）才呼叫 main；被其他程式 import 時不自動抓資料。
if __name__ == "__main__":
    main()
