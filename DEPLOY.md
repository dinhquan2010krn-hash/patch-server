# Deploy lên domain public (giống server cũ)

Server cũ chạy trên **Render.com** (`mduyk-key-server.onrender.com`). Làm theo các bước dưới để có domain riêng dạng `https://<tên>.onrender.com`.

---

## 1. Chọn tên service (QUAN TRỌNG)

App gốc hardcode domain `mduyk-key-server.onrender.com` (host dài **29 byte**, trong đó phần tên service là **16 ký tự**).

Muốn patch binary bằng `tools/patch_domain.py` thì **tên service mới cũng phải đúng 16 ký tự**, ví dụ:

```
mduyk-key-server   <- cũ (16)
mduyk-key-srv001   <- mới (16)  ✅ khuyến nghị
```

Domain mới sẽ là: `https://mduyk-key-srv001.onrender.com`

> Nếu bạn dùng tên khác độ dài, script patch sẽ báo lỗi. Có thể dùng custom domain nhưng cần đổi script cho phù hợp.

---

## 2. Đẩy project lên GitHub

```powershell
cd "D:\Users\ANH MY\Downloads\ThreeOneOSFiveServer"
git init
git add .
git commit -m "Initial patch server"
git remote add origin https://github.com/<USERNAME>/<REPO>.git
git push -u origin main
```

Tạo repo mới (public hoặc private) trên https://github.com/new rồi thay `<USERNAME>/<REPO>`.

---

## 3. Deploy trên Render

1. Vào https://dashboard.render.com → **New → Web Service**
2. Chọn repo GitHub vừa push.
3. Render sẽ tự nhận `render.yaml` (Blueprint) hoặc điền tay:
   - **Name**: `mduyk-key-srv001` (đúng 16 ký tự)
   - **Runtime**: Python 3.12
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn app:create_app --bind 0.0.0.0:$PORT`
   - **Plan**: Free
4. Trong **Environment**, điền:
   - `ADMIN_KEY` = khóa admin bạn muốn (bắt buộc)
   - `SERVER_SECRET_KEY` = chuỗi random bất kỳ
5. Bấm **Create Web Service**. Đợi build xong (~2–5 phút).

Sau đó test:

```
https://mduyk-key-srv001.onrender.com/health
https://mduyk-key-srv001.onrender.com/api/v1/content/config
https://mduyk-key-srv001.onrender.com/admin
```

---

## 4. Patch app để trỏ vào server mới

```powershell
cd "D:\Users\ANH MY\Downloads\ThreeOneOSFiveServer"
python tools/patch_domain.py "D:\Users\ANH MY\Downloads\ThreeOneOSFive" mduyk-key-srv001 "D:\Users\ANH MY\Downloads\ThreeOneOSFive_patched"
python tools/patch_domain.py --verify "D:\Users\ANH MY\Downloads\ThreeOneOSFive_patched"
```

Kết quả mong đợi: `Replaced 3 occurrence(s)`, `old host occurrences: 0`.

### Ký lại binary (bắt buộc trên macOS/arm64)

Sửa byte làm mất chữ ký code. Trên máy Mac:

```bash
codesign -s - --force "ThreeOneOSFive_patched"
# nếu app dùng hardened runtime:
codesign -s - --force --options runtime "ThreeOneOSFive_patched"
```

Nếu app được đóng gói trong IPA: thay binary trong `Payload/*.app/`, ký lại app, rồi đóng lại IPA.

---

## 5. Lưu ý về dữ liệu (quan trọng)

Render **free plan không có ổ cứng persistent**. Mỗi lần restart/redeploy:
- `instance/server.db` (license, token) và `instance/patches/*.3105` **sẽ bị mất**.

Giải pháp:
- **Fly.io + Volume** (miễn phí có volume nhỏ) — dùng `Dockerfile` có sẵn, mount volume vào `/app/instance`.
- **VPS** (Debian/Ubuntu) — chạy `docker build -t patch-server .` rồi mount thư mục `instance` ra host.
- Render trả phí + **Persistent Disk**, mount vào `/app/instance`.

Với mục đích test nhanh thì free Render là đủ.

---

## 6. Cấu hình admin sau khi deploy

Vào `https://<domain>/admin`, đăng nhập bằng `ADMIN_KEY` bạn đặt ở bước 3:
- Tạo license tại `/admin/licenses`
- Upload file `.3105` tại `/admin/patches`
- Config hiển thị tại `/api/v1/content/config`
