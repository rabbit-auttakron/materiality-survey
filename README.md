# 🌿 Materiality Assessment Survey – PET Plastic Industry

ระบบสำรวจ Materiality Assessment สำหรับอุตสาหกรรมพลาสติก PET  
ตามมาตรฐาน **GRI Standards 2021 (Single Materiality)**

---

## 📋 ฟีเจอร์

| หน้า | URL | รายละเอียด |
|------|-----|------------|
| หน้าหลัก | `/` | เลือกกลุ่มผู้มีส่วนได้เสีย |
| แบบสอบถาม | `/survey/<type>` | `investor / customer / employee / community / supplier` |
| ขอบคุณ | `/thanks` | หน้าหลังส่งแบบสอบถาม |
| Admin Login | `/admin` | เข้าสู่ระบบหลังบ้าน |
| Export CSV | `/export/csv` | ดาวน์โหลดข้อมูลทั้งหมด |

## 🗂️ โครงสร้างไฟล์

```
pet-survey/
├── app.py              ← Flask backend + SQLite
├── requirements.txt    ← Flask==3.0.3
├── Procfile            ← web: python app.py
├── runtime.txt         ← python-3.11.0
├── .gitignore
└── templates/
    ├── index.html      ← หน้าหลัก
    ├── survey.html     ← แบบสอบถาม (Jinja2)
    ├── thanks.html     ← หน้าขอบคุณ
    ├── admin_login.html
    └── admin.html      ← Dashboard + Charts
```

---

## 🚀 Deploy บน Railway (ไม่ต้องใช้ Docker หรือ package.json)

### ขั้นตอน

**1. สร้าง GitHub Repository**
```bash
git init
git add .
git commit -m "Initial commit: Materiality Survey System"
git remote add origin https://github.com/<your-username>/pet-survey.git
git push -u origin main
```

**2. Deploy บน Railway**
1. ไปที่ [railway.app](https://railway.app) → New Project
2. เลือก **Deploy from GitHub repo**
3. เลือก repo ที่สร้าง → Railway จะ auto-detect Python
4. ไปที่ **Settings → Variables** เพิ่ม:

| Variable | Value |
|----------|-------|
| `ADMIN_PASSWORD` | รหัสผ่านที่ต้องการ |
| `SECRET_KEY` | random string ยาว ๆ |
| `PORT` | (Railway ตั้งให้อัตโนมัติ) |

5. Deploy สำเร็จ → ได้ URL เช่น `https://pet-survey.up.railway.app`

### Railway ทำงานอย่างไร?
- อ่าน `runtime.txt` → ติดตั้ง Python 3.11
- อ่าน `requirements.txt` → ติดตั้ง Flask
- อ่าน `Procfile` → รัน `python app.py`
- **ไม่ต้องใช้ Docker หรือ package.json เลย**

---

## 🔐 Admin Dashboard

- URL: `/admin`
- รหัสผ่านเริ่มต้น: `admin1234` (เปลี่ยนใน Railway Variables)
- ฟีเจอร์:
  - 📊 สรุปจำนวนผู้ตอบ
  - 📈 กราฟ Doughnut แยกตามกลุ่ม
  - 🏆 อันดับประเด็น ESG ตามคะแนนเฉลี่ย
  - 🗺️ Materiality Heatmap ครอส 5 กลุ่ม
  - 💬 คำตอบเปิด (Open-ended)
  - ⬇️ Export CSV (รองรับ Excel/ภาษาไทย)

---

## 📊 กลุ่มผู้มีส่วนได้เสีย

| ชุด | กลุ่ม | จำนวนประเด็น |
|-----|-------|-------------|
| 1 | 💼 ผู้ถือหุ้น/นักลงทุน | 12 ประเด็น |
| 2 | 🛒 ลูกค้า/ผู้บริโภค | 9 ประเด็น |
| 3 | 👷 พนักงาน | 10 ประเด็น |
| 4 | 🌳 ชุมชนท้องถิ่น/NGO | 9 ประเด็น |
| 5 | 🏭 ซัพพลายเออร์ | 10 ประเด็น |

อ้างอิง: GRI 201, 205, 302–308, 401, 403–406, 408, 413, 416

---

## ⚠️ หมายเหตุ

- **SQLite** เหมาะสำหรับ MVP/ทดสอบ — หาก Railway redeploy ข้อมูลอาจหาย
- สำรองข้อมูลด้วย **Export CSV** ก่อน redeploy ทุกครั้ง
- สำหรับ production ควรเปลี่ยนไปใช้ Railway PostgreSQL
