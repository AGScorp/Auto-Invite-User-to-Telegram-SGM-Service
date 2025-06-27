# Telegram Channel & Group Invitation API

## การใช้งานด้วย Docker

### ข้อกำหนดเบื้องต้น
- Docker Engine 20.10+
- Docker Compose 1.29+
- Python 3.12 (ใน Docker image)

### การตั้งค่า

1. **สร้างไฟล์ `.env`** ในโฟลเดอร์เดียวกับ docker-compose.yml:
```env
# API Bearer Token
API_BEARER_TOKEN=your_secure_token_here

# Telegram Account 1
0917598103_api_id=12345678
0917598103_api_hash=abcdef1234567890abcdef1234567890
0917598103_phone_number=+66917598103

# Telegram Account 2
0912345678_api_id=87654321
0912345678_api_hash=1234567890abcdef1234567890abcdef
0912345678_phone_number=+66912345678
```

2. **สร้างโฟลเดอร์สำหรับ sessions** (ถ้ายังไม่มี):
```bash
mkdir -p sessions
```

### คำสั่งการใช้งาน

#### Build และ Run ด้วย Docker Compose
```bash
# Build image
docker-compose build

# Run service
docker-compose up -d

# ดู logs
docker-compose logs -f

# หยุด service
docker-compose down
```

#### Build และ Run ด้วย Docker (ไม่ใช้ Compose)
```bash
# Build image
docker build -t telegram-api .

# Run container
docker run -d \
  --name telegram-api \
  -p 8200:8200 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/sessions:/app/sessions \
  telegram-api
```

### การเข้าถึง API

- **API Documentation**: http://localhost:8200/docs
- **ReDoc**: http://localhost:8200/redoc
- **Health Check**: http://localhost:8200/

### Endpoints หลัก

1. **ส่งรหัสยืนยัน**
   ```
   GET /send_verification_code/{account_name}
   ```

2. **สร้าง Session**
   ```
   POST /create_session
   ```

3. **เชิญผู้ใช้เข้าช่อง/กลุ่ม**
   ```
   POST /invite_user_to_channal_or_group
   ```

4. **ตรวจสอบบัญชีที่ตั้งค่าไว้** (ต้องใช้ Bearer Token)
   ```
   GET /check_configured_accounts
   Headers: Authorization: Bearer {token}
   ```

### การแก้ปัญหา

#### Container ไม่ start
```bash
# ตรวจสอบ logs
docker-compose logs telegram-api

# ตรวจสอบ container status
docker ps -a
```

#### Permission denied
```bash
# ให้สิทธิ์ไฟล์ .env
chmod 600 .env

# ให้สิทธิ์โฟลเดอร์ sessions
chmod 755 sessions
```

#### Port 8200 ถูกใช้งานแล้ว
แก้ไขใน docker-compose.yml:
```yaml
ports:
  - "8201:8200"  # เปลี่ยนเป็น port อื่น
```

### การ Debug

เข้าไปใน container:
```bash
docker exec -it telegram-invitation-api bash
```

### การ Update

```bash
# Pull code ใหม่
git pull

# Rebuild และ restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Security Notes

1. **ไม่ควร commit ไฟล์ `.env`** ลง Git
2. ใช้ **strong Bearer Token** สำหรับ production
3. ควรใช้ **HTTPS** สำหรับ production deployment
4. จำกัดการเข้าถึง port 8200 ด้วย firewall

### Performance Tuning

สำหรับ production สามารถปรับ uvicorn workers:
```dockerfile
CMD ["uvicorn", "main:app_api", "--host", "0.0.0.0", "--port", "8200", "--workers", "4"]
```