# Viotp Login Tool

Đây là công cụ đăng nhập tự động vào hệ thống Viotp.com, có khả năng vượt qua lớp bảo vệ Cloudflare Turnstile và reCAPTCHA v2 Invisible.

## Cách hoạt động
1. Khởi chạy trình duyệt thật (Chrome/Chromium) thông qua DrissionPage để tải trang login.
2. Dừng chờ (tối đa 60s) để người dùng tự tay xác nhận Cloudflare.
3. Chạy lệnh execute ngầm để lấy token reCAPTCHA hợp lệ.
4. Lấy các cookies thiết yếu (như `cf_clearance`) từ phiên trình duyệt.
5. Gọi API Login trực tiếp bằng `curl_cffi` (giả lập TLS fingerprint của Chrome) để bypass các lớp chặn request.

## Yêu cầu thư viện:
```bash
pip install DrissionPage curl_cffi
```

## Cách sử dụng
Khởi chạy script trực tiếp:
```bash
python main.py
```
Sau đó nhập `Username` và `Password` khi được yêu cầu trên Terminal.

*Script sẽ mở trình duyệt, yêu cầu bạn xác nhận Cloudflare nếu có, chạy ngầm lấy token và trả về kết quả Login.*

## Author
👤 **@hieungguyen2907**
* Telegram: [t.me/hieunguyen2907](https://t.me/hieunguyen2907)
