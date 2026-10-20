# ================================================================
# 第 1 題｜本週新片資訊
# 使用技術：requests 取得開眼電影網 HTML，BeautifulSoup 擷取電影區塊。
# 流程說明：下載網頁 → 設定中文編碼 → 找到標題、簡介、上映資訊與連結 → 印出結果。
# 輸出內容：Console 中顯示電影資訊與筆數；本題沒有寫入 CSV。
# 報告提醒：requests 取得原始 HTML，不會開啟瀏覽器或執行網頁的 JavaScript。
# ================================================================

# 匯入 requests 套件：用來發送 HTTP 請求
import requests
# 匯入 BeautifulSoup 套件：用來解析 HTML 網頁內容
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 目標網站：開眼電影網的「本週新片」頁面
url = "https://www.atmovies.com.tw/movie/new/"

# 1. 發送 GET 請求，取得網頁原始內容
response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
# HTTP 4xx、5xx 會在這裡拋出例外，避免把錯誤頁當成資料解析。
response.raise_for_status()
# 2. 設定 HTTP 回應的編碼，避免中文出現亂碼
response.encoding = "utf-8"

# 3. 使用 BeautifulSoup 解析 HTML
# html.parser 是 Python 內建的 HTML 解析器
soup = BeautifulSoup(response.text, "html.parser")

# 4. 抓取電影列表區塊
# 實際網站結構中，每部電影都是 article 標籤，class 是 filmList
movie_items = soup.select("article.filmList")

# 5. 若沒有抓到資料，就輸出提示訊息
if not movie_items:
    print("找不到本週新片資料")
else:
    print("--- 本週新片上映資訊 ---")

    # 6. 逐一處理每一部電影
    count = 0
    for item in movie_items:
        # 抓取電影標題與其詳細頁面網址
        # .filmTitle a 代表電影名稱所在的超連結
        title_tag = item.select_one(".filmTitle a")
        if not title_tag:
            continue

        # 取得電影名稱文字
        title = title_tag.get_text(strip=True)
        # 組合完整網址（因為 href 是相對路徑）
        href = title_tag.get("href")
        if not href:
            continue
        link = urljoin(url, href)

        # 抓取電影簡介文字
        # 每部電影的敘述通常放在 p 標籤中
        content_tag = item.select_one("p")
        # get_text 取出標籤內的文字，strip=True 去掉頭尾空白；空格用來分隔子標籤文字。
        content = content_tag.get_text(" ", strip=True) if content_tag else "無內容說明"

        # 抓取片長與上映資訊
        # .runtime 這個 class 包含片長、上映日期、上映廳數等資訊
        runtime_tag = item.select_one(".runtime")
        runtime = runtime_tag.get_text(" ", strip=True) if runtime_tag else "無片長資訊"

        # 7. 輸出每部電影的資訊
        count += 1
        print(f"電影 {count}:")
        print(f"  標題: {title}")
        print(f"  內容: {content}")
        print(f"  片長/上映資訊: {runtime}")
        print(f"  網址: {link}")
        print("-" * 40)

    # 8. 顯示總數量
    print(f"總共成功抓取到 {count} 部新片資訊。")
