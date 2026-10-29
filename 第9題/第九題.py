# ================================================================
# 第 9 題｜Google 新聞區塊
# 使用技術：Selenium 開啟 Chrome、等待與捲動頁面，再用 JavaScript 讀取 DOM。
# 流程說明：載入動態內容 → 找指定分類 → 擷取新聞連結 → 去除重複 → 保存 CSV 與截圖。
# 輸出內容：google_news.csv：分類、新聞標題、網址；google_news.png：當下視窗截圖。
# 報告提醒：只收集當次載入且可辨識的內容；個人化分類可能未出現，不能宣稱涵蓋全部新聞。
# ================================================================

"""使用 Selenium 讀取 Google 新聞首頁的指定新聞區塊。"""

import csv
from pathlib import Path
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


URL = "https://news.google.com/home?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
OUTPUT_DIR = Path(__file__).resolve().parent
CSV_FILE = OUTPUT_DIR / "google_news.csv"
SCREENSHOT_FILE = OUTPUT_DIR / "google_news.png"
SECTION_NAMES = ["焦點新聞", "地方新聞", "您的主題", "更多新聞"]


def main():
    # 預設開啟可見的 Chrome，方便觀察 Selenium 如何載入動態內容。
    driver = webdriver.Chrome()
    try:
        driver.get(URL)
        # 顯式等待最多 20 秒，每次重新檢查條件；條件成立就繼續，不一定等滿 20 秒。
        wait = WebDriverWait(driver, 20)
        wait.until(
            lambda browser: browser.find_elements(
                By.XPATH, "//h2 | //h3 | //*[@role='heading']"
            )
        )

        # 往下捲動數次，讓延遲載入的新聞區塊出現在頁面中。
        previous_height = 0
        for _ in range(6):
            height = driver.execute_script("return document.body.scrollHeight")
            if height == previous_height:
                break
            previous_height = height
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

        driver.execute_script("window.scrollTo(0, 0)")
        wait.until(lambda browser: browser.find_elements(By.CSS_SELECTOR, "h3 a"))

        # 依畫面標題向上尋找含新聞連結的容器，再讀取容器中的新聞標題。
        # 這段字串是交給瀏覽器執行的 JavaScript：arguments[0] 接收 SECTION_NAMES。
        # 先比對分類標題，再向上找含新聞連結的容器，以 aria-label 作為新聞標題。
        records = driver.execute_script(
            """
            const wanted = arguments[0];
            const headings = Array.from(document.querySelectorAll(
              'h1, h2, h3, [role="heading"]'
            ));
            const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
            const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
            const output = [];
            for (const label of wanted) {
              const heading = headings.find(h => visible(h) && clean(h.innerText) === label);
              if (!heading) continue;
              let node = heading;
              let container = null;
              while (node && node !== document.body) {
                node = node.parentElement;
                if (!node) break;
                const nestedHeading = Array.from(node.querySelectorAll('h2, h3, [role="heading"]'))
                  .some(h => h !== heading && wanted.includes(clean(h.innerText)));
                if (nestedHeading) break;
                const links = Array.from(node.querySelectorAll('a[aria-label][href]'))
                  .filter(a => visible(a) && clean(a.getAttribute('aria-label'))
                    && a.href.includes('news.google.com/read'));
                if (links.length) { container = node; break; }
                if (node.matches('section')) break;
              }
              if (!container) continue;
              for (const a of container.querySelectorAll('a[aria-label][href]')) {
                const title = clean(a.getAttribute('aria-label'));
                if (visible(a) && title && a.href.includes('news.google.com/read')) {
                  output.push([label, title, a.href]);
                }
              }
            }
            return output;
            """,
            SECTION_NAMES,
        )

        # 焦點提要至少應能指出其下的兩個主要新聞入口。
        focus_links = driver.find_elements(
            By.XPATH,
            "//h2[normalize-space()='焦點新聞' or normalize-space()='地方新聞']/a | "
            "//*[@role='heading' and (normalize-space()='焦點新聞' or normalize-space()='地方新聞')]/a",
        )
        # 焦點提要記錄的是分類入口；它和各分類裡的單篇新聞連結用途不同。
        for link in focus_links:
            title = link.text.strip()
            href = link.get_attribute("href")
            if title and href:
                records.append(["焦點提要", title, href])

        # 去除相同區塊重複出現的新聞連結。
        unique_records = []
        seen = set()
        for record in records:
            # 用「分類、網址」作為唯一鍵：同分類同網址只留一筆，不同分類則可各自保留。
            key = (record[0], record[2])
            if key not in seen:
                seen.add(key)
                unique_records.append(record)

        # 分類入口不等於新聞；至少取得一篇指定分類的新聞才更新檔案。
        if not any(record[0] in SECTION_NAMES for record in unique_records):
            raise RuntimeError("沒有取得指定分類的新聞，未更新 google_news.csv")
        for section in ["焦點提要", *SECTION_NAMES]:
            titles = [record[1] for record in unique_records if record[0] == section]
            print(f"{section}：{titles}")

        # with 自動關檔；w 覆寫舊檔，newline 避免多餘換行，UTF-8 BOM 方便 Excel 辨識中文。
        with CSV_FILE.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["分類", "新聞標題", "網址"])
            writer.writerows(unique_records)

        driver.execute_script("window.scrollTo(0, 0)")
        driver.save_screenshot(str(SCREENSHOT_FILE))
        print(f"找到 {len(unique_records)} 筆新聞資料，已存入：{CSV_FILE}")
        print(f"頁面截圖已存入：{SCREENSHOT_FILE}")
        # 比對有無抓到各分類，列出缺少的區塊；缺少區塊不會阻止這支程式寫檔。
        missing = [name for name in SECTION_NAMES if not any(r[0] == name for r in unique_records)]
        if missing:
            print("頁面目前沒有顯示這些區塊（可能需登入或依帳號而異）：" + "、".join(missing))
    finally:
        # finally 在成功或發生例外時都會執行，確保 Chrome 與 WebDriver 正常關閉。
        driver.quit()


# 直接執行此檔（含 Spyder 執行檔案）才呼叫 main；被其他程式 import 時不自動抓資料。
if __name__ == "__main__":
    main()
