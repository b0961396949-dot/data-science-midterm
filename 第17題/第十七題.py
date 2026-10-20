# ================================================================
# 第 17 題｜Selenium 自動登入 GitHub 並擷取首頁
# 流程：讀取設定 → 沿用登入狀態或自動登入 → 擷取首頁與題目指定區塊。
# 不使用 input，不需要回 Console 按 Enter；登入失敗時不重複嘗試密碼。
# 題目截圖是舊版首頁；指定區塊不存在時會報告缺少，不用其他區塊冒充。
# ================================================================

import os
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# 首次使用：請在本機設定 GITHUB_USERNAME、GITHUB_PASSWORD 環境變數。
# 未設定環境變數時，優先沿用本機 Chrome 設定檔中的有效登入狀態。
# 這裡需要網頁登入密碼，不是 Personal Access Token（PAT）。
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "")
GITHUB_PASSWORD = os.environ.get("GITHUB_PASSWORD", "")

OUT_DIR = Path(__file__).resolve().parent
# 獨立的 Chrome 設定檔保留這個程式的登入狀態，不使用日常 Chrome 設定檔。
# 此資料夾包含登入狀態，繳交作業時只交程式與輸出檔。
PROFILE_DIR = OUT_DIR / ".github_chrome_profile"
DASHBOARD_URL = "https://github.com/dashboard"
BLOCK_TITLES = {
    "github_block1": "Create your first project",
    "github_block2": "Updates to your homepage feed",
}


def signed_in(driver):
    """以 GitHub 登入帳號標記判斷，不把公開頁面的 main 當作登入成功。"""
    location = urlparse(driver.current_url)
    if location.scheme != "https" or location.hostname != "github.com":
        return False
    return bool(driver.find_elements(By.CSS_SELECTOR, 'meta[name="user-login"][content]:not([content=""])'))


def extra_verification(driver):
    """辨識第二因素或新裝置確認；不將這些頁面當成 Dashboard。"""
    path = urlparse(driver.current_url).path.lower()
    return any(part in path for part in (
        "/sessions/two-factor", "/sessions/verified-device", "/sessions/verify",
        "/login/device", "/account_verifications", "/settings/two_factor_authentication",
    )) or bool(driver.find_elements(By.CSS_SELECTOR,
        'input[autocomplete="one-time-code"], input[name="otp"], #captcha-form, iframe[src*="captcha"]'))


def login_outcome(driver):
    """等待登入結果，錯誤與額外驗證也要立即回報。"""
    if extra_verification(driver):
        return "verification"
    if signed_in(driver):
        return "success"
    errors = driver.find_elements(By.CSS_SELECTOR, ".flash-error, #js-flash-container [role='alert']")
    if any(element.is_displayed() and element.text.strip() for element in errors):
        return "error"
    return False


def automatic_login(driver):
    """能沿用 Session 就直接進入；否則只自動送出一次帳密。"""
    driver.get(DASHBOARD_URL)
    WebDriverWait(driver, 30).until(lambda d: signed_in(d) or extra_verification(d)
        or d.find_elements(By.ID, "login_field"))
    if extra_verification(driver):
        raise ValueError("GitHub 要求額外安全驗證，目前無法全自動完成；未保存登入頁為作業結果。")
    if signed_in(driver):
        print("已沿用有效的 GitHub 登入狀態。", flush=True)
        return
    username = (GITHUB_USERNAME or os.environ.get("GITHUB_USERNAME", "")).strip()
    password = GITHUB_PASSWORD or os.environ.get("GITHUB_PASSWORD", "")
    if not username or not password:
        raise ValueError("尚未設定帳密。請在本機設定 GITHUB_USERNAME、GITHUB_PASSWORD 環境變數後執行。")
    # 僅在 GitHub 官方登入頁填入帳密。
    location = urlparse(driver.current_url)
    if location.scheme != "https" or location.hostname != "github.com":
        raise ValueError("目前不在 github.com，已停止送出帳密。")
    print("正在自動填寫帳密並登入……", flush=True)
    account_input = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "login_field")))
    account_input.clear()
    account_input.send_keys(username)
    password_input = driver.find_element(By.ID, "password")
    password_input.clear()
    password_input.send_keys(password)
    driver.find_element(By.CSS_SELECTOR, 'input[name="commit"], button[name="commit"]').click()
    result = WebDriverWait(driver, 30).until(login_outcome)
    if result == "verification":
        raise ValueError("GitHub 要求雙重驗證、新裝置驗證或安全驗證；本次無法全自動登入。")
    if result == "error":
        raise ValueError("GitHub 未接受登入，請確認帳密或帳號狀態；不會自動重試密碼。")


def capture_blocks(driver):
    """分別保存題目標題及其說明所在的區塊，不以整個側欄取代指定文字。"""
    missing = []
    for basename, title in BLOCK_TITLES.items():
        # 兩個題目標題沒有引號，可直接放入 XPath 字串常值。
        candidates = driver.find_elements(By.XPATH,
            f"//*[self::h2 or self::h3 or self::h4 or self::strong][normalize-space()='{title}']")
        visible = [element for element in candidates if element.is_displayed()]
        if not visible:
            missing.append(title)
            continue
        # 取最近且含段落的區塊，保存標題、說明、連結與區塊畫面。
        containers = visible[0].find_elements(By.XPATH,
            "ancestor::*[self::div or self::section][.//p][1]")
        if not containers:
            missing.append(title)
            continue
        block = containers[0]
        html = block.get_attribute("outerHTML")
        text = block.text
        if not html or not text.strip():
            missing.append(title)
            continue
        (OUT_DIR / f"{basename}.html").write_text(html, encoding="utf-8")
        (OUT_DIR / f"{basename}.txt").write_text(text, encoding="utf-8")
        if not block.screenshot(str(OUT_DIR / f"{basename}.png")):
            raise OSError("區塊截圖失敗")
        print(f"已擷取：{title}", flush=True)
    return missing


def main():
    driver = None
    try:
        print("第十七題：自動登入 GitHub、擷取首頁及指定區塊。", flush=True)
        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-data-dir={PROFILE_DIR}")
        options.add_argument("--window-size=1440,1100")
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(45)
        automatic_login(driver)
        # 登入後才前往 Dashboard，避免保存登入、驗證或公開宣傳頁。
        driver.get(DASHBOARD_URL)
        WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.TAG_NAME, "main")))
        if extra_verification(driver) or not signed_in(driver):
            raise ValueError("尚未確認 Dashboard 的登入狀態；本次未保存結果。")
        (OUT_DIR / "github_home.html").write_text(driver.page_source, encoding="utf-8")
        if not driver.save_screenshot(str(OUT_DIR / "github_home.png")):
            raise OSError("首頁截圖失敗")
        missing = capture_blocks(driver)
        if missing:
            print("首頁已保存，但題目尚未全部完成：目前頁面找不到下列指定區塊：", flush=True)
            for title in missing:
                print(f"  - {title}", flush=True)
            print("GitHub 版面與帳號狀態會影響這些區塊；舊的區塊檔案不代表本次結果。", flush=True)
        else:
            print("完成：登入、首頁與兩個指定區塊均已保存。", flush=True)
        print(f"輸出位置：{OUT_DIR}", flush=True)
    except ValueError as error:
        print(f"本次未完成：{error}", flush=True)
    except TimeoutException:
        print("本次未完成：等待 GitHub 頁面或登入結果逾時；沒有自動重試帳密。", flush=True)
    except WebDriverException:
        print("本次未完成：Chrome 操作中斷。請確認 Chrome 可啟動，且未同時執行本題。", flush=True)
    except OSError:
        print("本次未完成：輸出檔案寫入或截圖失敗，請檢查資料夾權限。", flush=True)
    except KeyboardInterrupt:
        print("已取消執行。", flush=True)
    finally:
        if driver is not None:
            try:
                driver.quit()
            except WebDriverException:
                pass


if __name__ == "__main__":
    main()
