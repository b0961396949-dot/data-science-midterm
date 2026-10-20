# ================================================================
# 第 15 題｜Google 搜尋 xpath 並嘗試更多結果
# 使用技術：Selenium 開啟搜尋網址、捲動頁面，並用 XPath 尋找更多結果按鈕。
# 流程說明：等待結果（遇驗證可手動完成）→ 最多嘗試 4 次捲動與點擊 → 收集連結 → 寫入 xpath.csv。
# 輸出內容：標題、超連結；同一網址只保留一次。
# 報告提醒：xpath 同時是搜尋關鍵字；XPath 也是此程式定位按鈕的方式。不能保證抓到全部結果。
# ================================================================

"""使用 Selenium 搜尋 Google 關鍵字 xpath，捲動並載入更多結果後輸出 xpath.csv。"""
import csv
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

QUERY = "xpath"
URL = "https://www.google.com/search?q=" + quote_plus(QUERY)
OUT = Path(__file__).resolve().parent / "xpath.csv"
MANUAL_VERIFY_SECONDS = 180  # 出現驗證頁時，保留 Chrome 等待手動操作的秒數。


def verification_required(driver):
    """辨識 Google 的流量驗證頁。"""
    return "/sorry/" in driver.current_url or bool(driver.find_elements(By.ID, "captcha-form"))


def results_loaded(driver):
    """確認已離開驗證頁，且搜尋結果的連結已載入。"""
    return not verification_required(driver) and bool(
        driver.find_elements(By.CSS_SELECTOR, "#search a[href] h3")
    )


def wait_for_results(driver):
    """遇到驗證時等使用者手動完成，成功返回搜尋結果後自動繼續。"""
    try:
        WebDriverWait(driver, 20).until(
            lambda d: verification_required(d) or results_loaded(d)
        )
    except TimeoutException:
        raise TimeoutException("20 秒內未載入搜尋結果，請檢查 Chrome 頁面與網路後再執行。") from None

    if verification_required(driver):
        print(
            f"Google 要求流量驗證，Chrome 會保留最多 {MANUAL_VERIFY_SECONDS} 秒。\n"
            "請切換到剛開啟的 Chrome，手動完成驗證；回到搜尋結果後，程式會自動繼續。",
            flush=True,
        )
        try:
            WebDriverWait(driver, MANUAL_VERIFY_SECONDS).until(results_loaded)
        except TimeoutException:
            raise TimeoutException(
                f"等待手動驗證逾時（{MANUAL_VERIFY_SECONDS} 秒），本次停止。"
                "若 Google 未提供可完成的驗證，請稍後再試。"
            ) from None
        print("已回到搜尋結果，繼續收集連結。", flush=True)


def main():
    driver = None
    try:
        driver = webdriver.Chrome()
        driver.set_page_load_timeout(45)
        driver.get(URL)
        wait_for_results(driver)
        # 最多操作四輪；找不到更多結果按鈕就停止，因此結果範圍是當次已載入內容。
        for _ in range(4):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            # XPath 同時找 a 或 button，文字包含中文或英文的更多結果，再保留可見元素。
            more = [b for b in driver.find_elements(By.XPATH, "//*[self::a or self::button][contains(., '更多結果') or contains(., 'More results')]") if b.is_displayed()]
            if more:
                more[0].click()
                wait_for_results(driver)
            else:
                break
        # 捲動或載入更多內容後也可能轉到驗證頁，收集前再確認一次。
        wait_for_results(driver)
        # rows 保留輸出順序，seen 集合專門用來檢查重複網址。
        rows, seen = [], set()
        # #search 限定搜尋結果容器；文字與網址皆非空且符合條件才加入結果。
        for a in driver.find_elements(By.CSS_SELECTOR, "#search a[href]"):
            href = a.get_attribute("href") or ""
            title = (a.text or "").strip()
            if href.startswith("http") and "google.com/" not in href and title and href not in seen:
                seen.add(href); rows.append([title, href])
        if not rows:
            print("沒有抓到可用搜尋結果，本次未寫入 CSV；若有舊檔會保留。")
            return
        # 先寫暫存檔，完整寫入後才替換 CSV，避免中途失敗破壞舊檔。
        temp_path = None
        try:
            with NamedTemporaryFile(
                mode="w", newline="", encoding="utf-8-sig",
                dir=OUT.parent, suffix=".csv.tmp", delete=False,
            ) as f:
                temp_path = Path(f.name)
                w = csv.writer(f)
                w.writerow(["標題", "超連結"])
                w.writerows(rows)
            temp_path.replace(OUT)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
        print(f"搜尋列內容：{QUERY}\n完成：{len(rows)} 筆，已存至 {OUT}")
    except TimeoutException as error:
        print(f"本次未完成：{error.msg}\n未寫入 CSV；若有舊檔會保留。")
    except WebDriverException as error:
        print(f"Chrome 操作中斷：{error.msg}\n未寫入 CSV；若有舊檔會保留。")
    except KeyboardInterrupt:
        print("已取消執行；若有舊 CSV 會保留。")
    finally:
        # finally 在成功或發生例外時都會執行，確保 Chrome 與 WebDriver 正常關閉。
        if driver is not None:
            try:
                driver.quit()
            except WebDriverException:
                pass  # 使用者可能已手動關閉 Chrome。


# 直接執行此檔（含 Spyder 執行檔案）才呼叫 main；被其他程式 import 時不自動抓資料。
if __name__ == "__main__":
    main()
