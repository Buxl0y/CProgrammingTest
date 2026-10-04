# C Programming Test — Full Stack Mini Online Judge

ระบบตัวอย่างสำหรับการสอบเขียนโปรแกรมภาษา C มี Login, Sidebar ข้อสอบ, Code Editor, Upload `.c`, Compile ด้วย GCC จริง, Test Cases (Public/Hidden), คำนวณคะแนน, Auto Save Draft, Submission History, Timer และ Admin Panel

## ความต้องการ

- Python 3.10+
- GCC / build-essential
- Linux/macOS/WSL สำหรับ resource limits

## เริ่มต้น

```bash
python3 server.py
```
เปิด `http://localhost:8000`

Student: `student` / `student123`
Admin: `admin` / `admin123`

SQLite จะสร้าง `data/app.db` และ seed ข้อสอบ 10 ข้ออัตโนมัติ

## Docker

```bash
docker compose up --build
```

## Security

Prototype นี้มี timeout และ Linux resource limits แต่ production ควรแยก compiler/executor worker ออกจาก API server และใช้ container/VM sandbox ที่ตัด network, จำกัด CPU/Memory/PIDs และใช้ non-root user
