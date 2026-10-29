# ================================================================
# 第 5 題｜台北週末電影票房
# 使用技術：requests 與 BeautifulSoup 先找排行榜入口，再取得 more 連結的完整頁面。
# 流程說明：取得排行榜首頁 → 追蹤 more 網址 → 解析巢狀表格 → 輸出 Taipei_movies.csv。
# 輸出內容：排名、片名、本週票房、累計票房。
# 報告提醒：至少取得 20 筆才更新 CSV，輸出來源順序的前 20 筆；不足時保留舊檔。
# ================================================================

import csv
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# 開眼電影網的台北週末票房排行榜首頁
ranking_url = "https://app2.atmovies.com.tw/boxoffice/"
headers = {"User-Agent": "Mozilla/5.0"}

# 輸出檔案放在本程式所在的資料夾
output_file = Path(__file__).resolve().parent / "Taipei_movies.csv"

print("[1/4] 正在取得開眼電影網票房排行榜...")
response = requests.get(ranking_url, headers=headers, timeout=30)
response.raise_for_status()
response.encoding = "utf-8"
print(f"[1/4] 網頁回應狀態：{response.status_code}")

soup = BeautifulSoup(response.text, "html.parser")

# 首頁只顯示前 5 名，因此找到「more」連結後，再開啟完整排行榜
# CSS 的 [href*=...] 表示網址中含指定字串，用來鎖定台北週末票房的 more 入口。
more_link = soup.select_one("a.viewMore[href*='twweekend']")
if not more_link:
    raise RuntimeError("找不到台北週末票房排行榜的 more 連結")

# urljoin 將網站回傳的相對路徑補成完整網址，再發出第二次請求。
full_url = urljoin(ranking_url, more_link["href"])
print(f"[2/4] 正在開啟完整排行榜：{full_url}")
full_response = requests.get(full_url, headers=headers, timeout=30)
full_response.raise_for_status()
full_response.encoding = "utf-8"
full_soup = BeautifulSoup(full_response.text, "html.parser")

# 完整排行榜的 HTML 將每部電影拆成兩個巢狀列：第一列放排名與片名，
# 第二列放票房與其他統計資料。先找到片名列，再從裡面的資料列取得本週票房。
movies = []
for title_cell in full_soup.select("td.at11"):
    title_row = title_cell.find_parent("tr")
    if title_row is None:
        continue
    # recursive=False 只找目前列直接包含的儲存格，避免誤取內層表格的格子。
    rank_cell = title_row.find("td", recursive=False)
    title_tag = title_cell.find("a")
    data_row = title_row.find("tr", bgcolor="C4DCC0")
    data_cells = data_row.find_all("td", recursive=False) if data_row else []

    # 先確認必要欄位存在，再用索引讀取票房，避免缺欄位時發生 IndexError。
    if not rank_cell or not title_tag or len(data_cells) < 4:
        continue

    rank = rank_cell.get_text(" ", strip=True)
    current_box_office = data_cells[2].get_text(" ", strip=True)
    cumulative_box_office = data_cells[3].get_text(" ", strip=True)

    # 保留來源排名欄的原始文字（包括「-」）；此處僅排除空白欄位。
    if not rank:
        continue

    movies.append([
        rank,
        title_tag.get_text(" ", strip=True),
        current_box_office,
        cumulative_box_office,
    ])

if len(movies) < 20:
    raise RuntimeError(f"只取得 {len(movies)} 筆，未滿題目要求的 20 筆；沒有更新舊 CSV")
movies = movies[:20]
for rank, title, current, cumulative in movies:
    print(f"{rank}｜{title}｜本週：{current}｜累計：{cumulative}")
print(f"[3/4] 已確認 {len(movies)} 筆票房資料，正在寫入 CSV...")

with output_file.open("w", newline="", encoding="utf-8-sig") as file:
    writer = csv.writer(file)
    writer.writerow(["排名", "片名", "本週票房", "累計票房"])
    writer.writerows(movies)

print(f"[4/4] 完成！資料已存入：{output_file}")
