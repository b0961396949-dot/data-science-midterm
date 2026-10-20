# ================================================================
# 第 6 題｜三支 NBA 球隊的球員名單
# 使用技術：requests 讀取 Basketball Reference，BeautifulSoup 解析 roster 表格。
# 流程說明：輪流代入球隊代碼 → 找球員表格 → 按 data-stat 欄位擷取 → 合併為 players.csv。
# 輸出內容：球隊、背號、姓名、位置、體重、生日、經驗、大學。
# 報告提醒：網址中的 2024 指指定賽季；體重等數值保留原網站單位，沒有做換算。
# ================================================================

"""擷取 Basketball Reference 2024 賽季三隊名單，輸出 players.csv。"""
import csv
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# CLE、HOU、GSW 分別是騎士、火箭、勇士的網站球隊代碼。
TEAMS = ["CLE", "HOU", "GSW"]
BASE = "https://www.basketball-reference.com/teams/{team}/2024.html"
FIELDS = ["球隊", "背號", "姓名", "位置", "體重", "生日", "經驗", "大學"]
OUT = Path(__file__).resolve().parent / "players.csv"


def main():
    rows = []
    # 同一段程式重複抓三個網址；format 會把 {team} 替換成當次球隊代碼。
    for team in TEAMS:
        response = requests.get(BASE.format(team=team), headers={"User-Agent": "Mozilla/5.0 (compatible; StudentProject/1.0)"}, timeout=25)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # #roster 是 CSS 的 id 選擇器，限定只解析球員名單表格。
        table = soup.select_one("#roster")
        if table is None:
            raise RuntimeError(f"{team} 名單表格不存在（網站可能回傳封鎖頁）")
        for tr in table.select("tbody tr"):
            # 有些表格會在資料列之間插入重複表頭，這裡先排除。
            if "thead" in (tr.get("class") or []):
                continue
            # 把取欄位的動作封裝成小函式；用 data-stat 名稱查找，比只依欄位位置清楚。
            def val(stat):
                cell = tr.select_one(f'[data-stat="{stat}"]')
                return cell.get_text(" ", strip=True) if cell else ""
            name = val("player")
            if name:
                # 大學欄嘗試兩種欄位名稱；缺少資料時保留空字串，不自行補值。
                rows.append([team, val("number"), name, val("pos"), val("weight"), val("birth_date"), val("years_experience"), val("college") or val("college_name")])
    # with 自動關檔；w 覆寫舊檔，newline 避免多餘換行，UTF-8 BOM 方便 Excel 辨識中文。
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(FIELDS); w.writerows(rows)
    print(f"完成：{len(rows)} 位球員，已存至 {OUT}")


# 直接執行此檔（含 Spyder 執行檔案）才呼叫 main；被其他程式 import 時不自動抓資料。
if __name__ == "__main__":
    main()
