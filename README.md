# ThreeOneOSFive Local Patch Server

Server Flask tự host, tương thích giao thức của app `ThreeOneOSFive` / `XAVION VN`:

- Xác thực license key (`/api/v1/activate`)
- Cấp access token (`/api/v1/get_token`)
- Trả catalog patch (`/api/v1/content/config`)
- Tải file patch `.3105` (`/api/v1/download/file/<file>/<uid>/<token>`)
- **Giao diện admin để tạo license và upload file patch `.3105`**

## Cài đặt & chạy

```powershell
cd "D:\Users\ANH MY\Downloads\ThreeOneOSFiveServer"
python -m pip install -r requirements.txt
python seed.py          # tao license demo (co the bo qua)
python app.py
```

Mở http://127.0.0.1:5000 — đăng nhập admin bằng `admin123` (mặc định).

Đổi admin key / secret trước khi dùng thật:

```powershell
$env:ADMIN_KEY = "my-secret-key"
$env:SERVER_SECRET_KEY = "some-random-string"
python app.py
```

Chạy production (gunicorn):

```powershell
gunicorn -w 2 -b 0.0.0.0:5000 app:create_app
```

## Dùng giao diện admin

| Trang | Chức năng |
|---|---|
| `/admin` | Tổng quan (số license, token, patch…) |
| `/admin/licenses` | Tạo / revoke license, đặt số ngày, max devices |
| `/admin/patches` | **Upload nhiều file `.3105`**, bật/tắt, tải lại, xóa |
| `/admin/config` | Sửa brand, notice, version, maintenance… trả về `/api/v1/content/config` |

File patch được lưu trong `instance/patches/` (tên lưu ngẫu nhiên, tên gốc nằm trong DB để tránh path traversal).

## API

| Method | Endpoint | Body / Ghi chú |
|---|---|---|
| POST | `/api/v1/activate` | `{"key":"...","deviceId":"...","bundleId":"...","appVersion":"..."}` |
| POST | `/api/v1/get_token` | `{"key":"...","deviceId":"..."}` → `token`, `uid`, `expires_at`, `expires_in` |
| POST | `/api/v1/download/token` | alias của `get_token` |
| GET | `/api/v1/content/config` | catalog public |
| GET | `/api/v1/version` | phiên bản |
| GET | `/health` | health check |
| GET | `/api/v1/download/file/<filename>/<uid>/<token>` | tải patch (token phải còn hạn) |

Ví dụ:

```powershell
$b = '{"key":"MDUYK-DEMO000000000000-DEMO0001","deviceId":"MY-DEVICE-01"}' |
     Set-Content -Path "$env:TEMP\req.json" -Encoding utf8
curl.exe -s -X POST http://127.0.0.1:5000/api/v1/activate `
  -H "Content-Type: application/json" --data-binary "@$env:TEMP\req.json"
curl.exe -s -X POST http://127.0.0.1:5000/api/v1/get_token `
  -H "Content-Type: application/json" --data-binary "@$env:TEMP\req.json"
```

## Lưu ý quan trọng

App gốc có **hardcoded** `https://mduyk-key-server.onrender.com`. Để app dùng server này bạn cần trỏ domain đó về máy bạn (sửa hosts + cert locally trusted) hoặc patch lại binary/cấu hình app. API ở trên đã được dựng đúng format để app nhận diện.

Dữ liệu nằm tại `instance/server.db` (SQLite) và `instance/patches/`. Xóa 2 mục này để reset.

## Deploy lên domain public

Xem **[DEPLOY.md](DEPLOY.md)** để deploy lên Render.com (domain `*.onrender.com` giống server cũ),
kèm script `tools/patch_domain.py` để sửa app trỏ vào server mới.

Tóm tắt nhanh:
```powershell
python tools/patch_domain.py <binary_goc> mduyk-key-srv001 <binary_moi>
```
Tên service phải đúng **16 ký tự** để patch được binary.

**Không có Git?** Xem **[DEPLOY_NOGIT.md](DEPLOY_NOGIT.md)** — deploy qua PythonAnywhere
(chỉ upload zip bằng trình duyệt) hoặc Render + Docker Hub.

**Patch files:** 20 file `.3105` đã được import từ `XAVION VN PATCH` vào DB + `instance/patches/`.
- `patch_server_full.zip` (11.58 MB) = code + DB + 20 patch → dùng để deploy.
- `patch_server_upload.zip` = chỉ code → dùng khi muốn thêm patch mới từ admin.
- Import lại từ thư mục gốc: `python tools/import_patches.py "<thư mục patch>"`
