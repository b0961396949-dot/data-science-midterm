# ================================================================
# 第 13 題｜momo 自動輸入 NBA
# 使用技術：Selenium 尋找搜尋欄，輸入 nba 並按 Enter，保存 page_source。
# 流程說明：等候搜尋欄 → 選取可見欄位 → 清除文字並送出搜尋 → 保存 NBA_test.html。
# 輸出內容：UTF-8 編碼的 HTML 檔，保存在本程式旁。
# 報告提醒：保存的是當下 DOM 的 HTML；沒有下載圖片等資源，離線開啟可能不完整。
# ================================================================

"""以 Selenium 開啟 momo 並搜尋 NBA，保存搜尋結果頁 HTML。"""
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://www.momoshop.com.tw/"
OUT = Path(__file__).resolve().parent / "NBA_test.html"


def main():
    driver = webdriver.Chrome()
    try:
        driver.get(URL)
        wait = WebDriverWait(driver, 25)
        # 同時嘗試多種搜尋欄選擇器，等候元素出現後再選取其中可見的一個。
        wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, "input[name='search-input'], input[type='search'], input[placeholder*='搜尋'], input[placeholder*='商品']"))
        candidates = driver.find_elements(By.CSS_SELECTOR, "input[name='search-input'], input[type='search'], input[placeholder*='搜尋'], input[placeholder*='商品']")
        # next(..., None) 找到第一個可見欄位；都沒有時回傳 None，交給下面處理。
        search = next((x for x in candidates if x.is_displayed()), None)
        if search is None:
            raise RuntimeError("找不到 momo 搜尋欄；請確認網站是否改版或出現驗證頁")
        # clear 清除舊文字，send_keys 模擬輸入 nba，Keys.ENTER 模擬按下 Enter。
        search.clear(); search.send_keys("nba", Keys.ENTER)
        # 此條件也可能因頁面已有超過 20 個連結而提早成立，並不保證商品全部載入。
        wait.until(lambda d: "search" in d.current_url.lower() or "keyword" in d.current_url.lower() or len(d.find_elements(By.CSS_SELECTOR, "a[href]")) > 20)
        # page_source 保存當下 HTML 字串；write_text 指定 UTF-8 避免中文編碼不一致。
        OUT.write_text(driver.page_source, encoding="utf-8")
        print(f"搜尋頁已存至 {OUT}\n目前網址：{driver.current_url}")
    finally:
        # finally 在成功或發生例外時都會執行，確保 Chrome 與 WebDriver 正常關閉。
        driver.quit()


# 直接執行此檔（含 Spyder 執行檔案）才呼叫 main；被其他程式 import 時不自動抓資料。
if __name__ == "__main__":
    main()
