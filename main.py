
from DrissionPage import ChromiumPage, ChromiumOptions
from curl_cffi import requests as cffi_requests
import json
import time
import sys
import re


LOGIN_PAGE = "https://viotp.com/en/account/login"
LOGIN_API_URL = "https://viotp.com/en//api/AccountAPI/Login"
SITE_KEY = "6LdtnN8pAAAAAIpXKeIEkqgMzh7QyK8aVHeKZiSH"


def get_captcha_token_browser(page: ChromiumPage) -> str | None:
    """
    Dùng browser thật để execute reCAPTCHA và lấy token hợp lệ
    """
    print("> Đang execute reCAPTCHA trong browser...")

    try:
        for i in range(15):
            ready = page.run_js("return typeof grecaptcha !== 'undefined' && typeof grecaptcha.execute === 'function'")
            if ready:
                break
            time.sleep(1)
        else:
            print("  ~ grecaptcha không sẵn sàng sau 15s")
            return None

        print("  ~ grecaptcha đã sẵn sàng, đang execute...")

        token = page.run_js(f"""
            return new Promise((resolve, reject) => {{
                try {{
                    grecaptcha.execute('{SITE_KEY}', {{action: 'submit'}}).then(function(token) {{
                        resolve(token);
                    }}).catch(function(err) {{
                        // Thử cách khác - execute không có action
                        grecaptcha.execute('{SITE_KEY}').then(function(token) {{
                            resolve(token);
                        }}).catch(function(err2) {{
                            reject(err2);
                        }});
                    }});
                }} catch(e) {{
                    // Thử grecaptcha.enterprise
                    try {{
                        grecaptcha.execute().then(function(token) {{
                            resolve(token);
                        }});
                    }} catch(e2) {{
                        reject(e2);
                    }}
                }}
            }});
        """, timeout=20)

        if token and len(token) > 50:
            print(f"  ~ reCAPTCHA token (JS execute): {token[:80]}...")
            return token

    except Exception as e:
        print(f"  ~ JS execute lỗi: {e}")

    print("  ~ Thử lấy token từ textarea...")
    try:
        token = page.run_js("""
            return new Promise((resolve, reject) => {
                // Callback khi captcha xong
                window.__captchaCallback = function(token) {
                    resolve(token);
                };
                
                // Thử nhiều cách
                try {
                    // Cách 1: execute trực tiếp
                    grecaptcha.execute();
                } catch(e) {}
                
                // Đợi token xuất hiện trong textarea
                let attempts = 0;
                let interval = setInterval(function() {
                    let el = document.querySelector('#g-recaptcha-response') 
                          || document.querySelector('[name="g-recaptcha-response"]')
                          || document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (el && el.value && el.value.length > 50) {
                        clearInterval(interval);
                        resolve(el.value);
                    }
                    attempts++;
                    if (attempts > 30) {
                        clearInterval(interval);
                        reject('timeout');
                    }
                }, 500);
            });
        """, timeout=20)

        if token and len(token) > 50:
            print(f"  ~ reCAPTCHA token (textarea): {token[:80]}...")
            return token

    except Exception as e:
        print(f"  ~ Textarea fallback lỗi: {e}")

    print("  ~ Thử trigger qua form submit...")
    try:
        page.run_js("""
            let btn = document.querySelector('button[type="submit"]') 
                   || document.querySelector('input[type="submit"]')
                   || document.querySelector('.btn-login')
                   || document.querySelector('[onclick*="submit"]');
            if (btn) btn.click();
        """)
        time.sleep(3)

        token = page.run_js("""
            let el = document.querySelector('#g-recaptcha-response') 
                  || document.querySelector('[name="g-recaptcha-response"]')
                  || document.querySelector('textarea[name="g-recaptcha-response"]');
            return el ? el.value : null;
        """)

        if token and len(token) > 50:
            print(f"  ~ reCAPTCHA token (form submit): {token[:80]}...")
            return token

    except Exception as e:
        print(f"  ~ Form submit lỗi: {e}")

    print("  ~ Không lấy được reCAPTCHA token")
    return None


def get_cookies_from_browser(page: ChromiumPage) -> dict:
    """
    Lấy tất cả cookies từ browser (bao gồm cf_clearance)
    """
    cookies = {}
    for cookie in page.cookies():
        cookies[cookie.get("name", "")] = cookie.get("value", "")
    return cookies


def login_api(username: str, password: str, captcha_token: str, cookies: dict) -> dict | None:
    """
    Gọi API login với curl_cffi (impersonate Chrome)
    """
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://viotp.com",
        "referer": "https://viotp.com/en/account/login",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }

    payload = {
        "Username": username,
        "Password": password,
        "GoogleCaptcha": captcha_token,
    }

    print(f"\n> Đang login API: {username}")
    print(f"  GoogleCaptcha: {captcha_token[:60]}...")

    try:
        resp = cffi_requests.post(
            LOGIN_API_URL,
            headers=headers,
            cookies=cookies,
            json=payload,
            impersonate="chrome",
            timeout=15,
        )

        print(f"  Status: {resp.status_code}")

        try:
            result = resp.json()
            print(f"  Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result
        except (json.JSONDecodeError, ValueError):
            print(f"  Text: {resp.text[:500]}")
            return None

    except Exception as e:
        print(f"  ~ Lỗi: {e}")
        return None


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    username = input("  Username: ").strip()
    password = input("  Password: ").strip()

    if not username or not password:
        print("  ~ Cần nhập username và password!")
        sys.exit(1)

    print("> Đang mở browser và load trang login...")
    co = ChromiumOptions()
    co.set_argument("--no-first-run")
    co.set_argument("--no-default-browser-check")
    co.set_argument("--disable-gpu")
    co.auto_port()

    page = ChromiumPage(co)
    page.get(LOGIN_PAGE)

    print("  ~ Đợi trang load...")
    for i in range(60):
        time.sleep(1)

        try:
            ready = page.run_js("return document.readyState")
            has_login = page.run_js("""
                return !!(document.querySelector('input[type="text"]') 
                       || document.querySelector('input[name*="user"]')
                       || document.querySelector('input[name*="User"]')
                       || document.querySelector('.login-form')
                       || document.querySelector('form'));
            """)
            if ready == "complete" and has_login and "login" in page.url.lower():
                break
        except:
            pass

    else:
        print("  ~ Trang không load được sau 60s")
        page.quit()
        sys.exit(1)

    print(f"  ~ Trang đã load: {page.url}")
    time.sleep(3)

    captcha_token = get_captcha_token_browser(page)

    cookies = get_cookies_from_browser(page)
    cf = cookies.get("cf_clearance", "N/A")
    print(f"  ~ cf_clearance: {cf[:50]}...")

    page.quit()

    if not captcha_token:
        print("\n~ Không lấy được reCAPTCHA token, dừng lại.")
        sys.exit(1)

    result = login_api(username, password, captcha_token, cookies)

if __name__ == "__main__":
    main()
