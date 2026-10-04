# Security Notes

ระบบนี้มี C compiler และ execute code จากผู้ใช้งาน จึงต้องถือว่า source code เป็น untrusted input

Prototype defenses:
- จำกัด source code 1 MB
- compile timeout 5 วินาที
- run timeout 2 วินาทีต่อ test case
- Linux resource limits
- HttpOnly/SameSite session cookie
- PBKDF2-HMAC-SHA256 password hashing
- ไม่ส่ง Hidden Test Case ไป Frontend

Production requirements:
1. แยก API server และ compiler workers
2. ใช้ container/VM ที่ตัด network/filesystem access
3. non-root execution user
4. read-only image + ephemeral workspace
5. จำกัด CPU/Memory/PID/IO และ kill process tree
6. seccomp/AppArmor/SELinux หรือ sandbox technology
7. Queue jobs ผ่าน Redis/RabbitMQ
8. Rate limit submission และ upload
9. Validate/escape output ก่อน render
10. เปลี่ยน demo passwords ก่อนใช้งานจริง
