# Deploy KHÔNG dùng Git

Chọn 1 trong 2 cách dưới. Cách 1 dễ nhất, chỉ dùng trình duyệt.

=====================================================================
## CÁCH 1 — PythonAnywhere (dễ nhất, không cài gì thêm)
=====================================================================

Domain kết quả: `https://<username>.pythonanywhere.com`

### Bước 1 — Tạo tài khoản
1. Vào https://www.pythonanywhere.com/registration/register/beginner/
2. Đăng ký (gói **Beginner / Free** là đủ).

### Bước 2 — Upload project
1. Vào **Dashboard** → tab **Files**.
2. Vào thư mục home của bạn (`/home/<username>/`).
3. Bấm **Upload a file** → chọn file:
   ```
   D:\Users\ANH MY\Downloads\ThreeOneOSFiveServer\patch_server_full.zip
   ```
   ⚠️ Dùng bản **full** (11.58 MB) — đã chứa sẵn DB + 20 file patch `.3105`.
   (`patch_server_upload.zip` chỉ là code, dùng khi muốn upload patch từ đầu.)
4. Sau khi upload xong, bấm **New directory**, đặt tên `patchserver`.
5. Vào thư mục `patchserver` → bấm **Upload a file** → upload lại zip đó vào đây.
6. Mở tab **Consoles** → bấm **Bash**. Trong console gõ:
   ```bash
   cd ~/patchserver
   unzip patch_server_full.zip
   ls
   ```
   Phải thấy `app.py`, `wsgi.py`, `admin.py`, ...

### Bước 3 — Cài Flask
Trong Bash console vừa mở:
```bash
python3 -m pip install --user flask gunicorn
```

### Bước 4 — Tạo Web app
1. Vào tab **Web** → bấm **Add a new web app**.
2. Chọn **Manual configuration** → **Python 3.10** (hoặc 3.11/3.12).
3. Sau khi tạo xong, trong trang Web app tìm dòng **Source code** → sửa thành:
   ```
   /home/<username>/patchserver
   ```
4. Tìm dòng **WSGI configuration file** → bấm vào link để sửa.
   Xóa toàn bộ nội dung, thay bằng:
   ```python
   import sys
   path = '/home/<username>/patchserver'
   if path not in sys.path:
       sys.path.insert(0, path)
   from wsgi import application
   ```
   Thay `<username>` bằng username PythonAnywhere của bạn. Bấm **Save**.

### Bước 5 — Đặt ADMIN_KEY
Trong trang Web app, mục **Environment variables**, thêm:
- Name: `ADMIN_KEY` — Value: khóa admin bạn muốn
- Name: `SERVER_SECRET_KEY` — Value: chuỗi random bất kỳ

### Bước 6 — Reload & test
1. Bấm nút xanh **Reload** trong tab Web.
2. Mở:
   ```
   https://<username>.pythonanywhere.com/health
   https://<username>.pythonanywhere.com/admin
   ```
3. Đăng nhập admin bằng `ADMIN_KEY`, upload patch tại `/admin/patches`.

### Bước 7 — Patch app trỏ vào domain này
Domain PythonAnywhere không dài 29 byte như domain Render, nên script cần chế độ đệm:

```powershell
cd "D:\Users\ANH MY\Downloads\ThreeOneOSFiveServer"
python tools/patch_domain.py "D:\Users\ANH MY\Downloads\ThreeOneOSFive" ^
  --domain "<username>.pythonanywhere.com" "D:\Users\ANH MY\Downloads\ThreeOneOSFive_patched"
```

Nếu domain mới **dài hơn 29 ký tự**, script sẽ báo — hãy chọn username ngắn hoặc dùng Cách 2.

=====================================================================
## CÁCH 2 — Render + Docker Hub (giữ nguyên domain 16 ký tự)
=====================================================================

Dùng khi bạn muốn domain đúng chuẩn `mduyk-key-srv001.onrender.com` để patch binary dễ dàng.

### Bước 1 — Cài Docker Desktop
Tải https://www.docker.com/products/docker-desktop/ rồi cài (chọn Windows).

### Bước 2 — Tạo tài khoản Docker Hub
Vào https://hub.docker.com/signup, tạo username (vd `myuser`).

### Bước 3 — Build & push image
```powershell
cd "D:\Users\ANH MY\Downloads\ThreeOneOSFiveServer"
docker login
docker build -t myuser/patch-server:latest .
docker push myuser/patch-server:latest
```

### Bước 4 — Deploy trên Render
1. https://dashboard.render.com → **New** → **Web Service**
2. Chọn **Deploy an existing image from a registry** → Docker Hub → chọn `myuser/patch-server:latest`.
3. Điền:
   - **Name**: `mduyk-key-srv001` (đúng 16 ký tự)
   - **Region**: Singapore
   - **Instance Type**: Free
4. Thêm 2 env var: `ADMIN_KEY`, `SERVER_SECRET_KEY`.
5. **Create Web Service** → đợi Live.

### Bước 5 — Patch app
```powershell
python tools/patch_domain.py "D:\Users\ANH MY\Downloads\ThreeOneOSFive" mduyk-key-srv001 "D:\Users\ANH MY\Downloads\ThreeOneOSFive_patched"
```

=====================================================================
## So sánh nhanh
=====================================================================
| | PythonAnywhere | Render + Docker |
|---|---|---|
| Cài đặt | Không | Docker Desktop (~500MB) |
| Upload | Zip qua web | Docker push |
| Domain | `<username>.pythonanywhere.com` | `mduyk-key-srv001.onrender.com` |
| Patch binary | Cần domain ngắn | Dễ (đúng 16 ký tự) |
| Lưu dữ liệu | Có (file system) | Mất khi restart (free) |

**Khuyến nghị**: nếu bạn chỉ cần test nhanh → Cách 1. Nếu muốn y hệt server cũ → Cách 2.
