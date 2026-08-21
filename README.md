# 💧 NumMaiLai (น้ำไม่ไหล)
### ระบบแจ้งเตือนเหตุน้ำประปาไม่ไหลและการซ่อมบำรุงท่อ การประปานครหลวง (MWA) ผ่าน Discord

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Discord](https://img.shields.io/badge/Discord-Webhook-5865F2?logo=discord&logoColor=white)](https://discord.com)

**NumMaiLai (น้ำไม่ไหล)** คือแอปพลิเคชันตรวจสอบและแจ้งเตือนเหตุน้ำประปาไม่ไหล, ท่อแตกรั่วฉุกเฉิน, งานตัดบรรจบท่อ, และงานบำรุงรักษาระบบท่อประปาจากการประปานครหลวง ([gisonline.mwa.co.th](https://gisonline.mwa.co.th/GIS1125/index-desktop.php)) แบบ Real-time โดยจะแจ้งเตือนเข้าสู่ **Discord Webhook** ทันทีเมื่อเกิดเหตุการณ์ในพื้นที่ที่คุณระบุ

---

## ✨ ฟีเจอร์เด่น (Key Features)

- 🎯 **ระบบกรองพื้นที่แบบ Hybrid (Hybrid Area Matching)**:
  - 📍 **GPS Proximity Radius**: คำนวณระยะทางจริงจากพิกัดบ้าน/ที่ทำงานของคุณ (Haversine Formula) เช่น ภายในรัศมี 3 หรือ 5 กม.
  - 🔑 **Thai Keyword Search**: ตรวจจับชื่อถนน, ซอย, ตำบล หรือชื่อหมู่บ้านในข้อความพื้นที่ผลกระทบ เช่น `"ประชาอุทิศ"`, `"พระราม 5"`, `"ราชพฤกษ์"`
  - 🏢 **MWA Branch Filter**: เลือกเฉพาะสาขาที่รับผิดชอบบ้านคุณ (เช่น สาขามหาสวัสดิ์, สาขาแม้นศรี, สาขาบางเขน)
- 💬 **การแจ้งเตือน Discord Webhook แบบ Rich Embeds**:
  - สีและสัญลักษณ์จำแนกตามความเร่งด่วน (🔴 แดง = ท่อแตกรั่วฉุกเฉิน / 🟠 ส้ม = ปิดประตูน้ำ / 🔵 ฟ้า = ตัดบรรจบท่อ / 🟡 เหลือง = Step Test & ตรวจสอบระบบ)
  - แสดงช่วงเวลาเริ่ม - สิ้นสุด, จุดปฏิบัติงาน, ขนาดท่อ, และเหตุผลที่แจ้งเตือนคุณ
  - มีลิงก์เปิดดูพิกัดบน **Google Maps** ทันทีด้วยคลิกเดียว
- 🗺️ **Interactive Web Dashboard**:
  - แผนที่แสดงจุดเกิดเหตุทั้งหมดใน กทม., นนทบุรี, สมุทรปราการ ผ่าน Leaflet / OpenStreetMap
  - คลิกบนแผนที่หรือลากหมุดเพื่อระบุตำแหน่งบ้าน พร้อมวงกลมแสดงรัศมีการแจ้งเตือนแบบสด
  - มีปุ่มทดสอบส่งการแจ้งเตือนไปยัง Discord ได้ทันที
- 🛡️ **ระบบป้องกันการแจ้งเตือนซ้ำ (Deduplication State)**:
  - บันทึกประวัติเหตุการณ์ลงใน `data/state.json` ทำให้แจ้งเตือนเพียงครั้งเดียวต่อเหตุการณ์ใหม่
- ⚙️ **ยืดหยุ่นในการรัน**: รองรับทั้งแบบคำสั่งเดียว (CLI/Cron), เบื้องหลังตลอด 24 ชม. (Daemon/Systemd), Web UI, หรือ Docker

---

## 🚀 เริ่มต้นใช้งานด่วน (Quick Start)

### 1. ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

### 2. ตั้งค่า Configuration (`config.yaml`)
คัดลอกไฟล์ตัวอย่างหรือแก้ไขไฟล์ `config.yaml`:
```bash
cp config.example.yaml config.yaml
```

ใส่ **Discord Webhook URL** ของคุณใน `config.yaml`:
```yaml
matching:
  mode: "hybrid" # แจ้งเตือนเมื่อตรงกับรัศมีพิกัด หรือ คำค้นหา หรือ สาขา
  location:
    enabled: true
    latitude: 13.824096   # พิกัดบ้านของคุณ
    longitude: 100.447783 # พิกัดบ้านของคุณ
    radius_km: 5.0        # รัศมีการแจ้งเตือน (กิโลเมตร)

  keywords:
    enabled: true
    terms:
      - "ประชาอุทิศ"
      - "พระราม 5"
      - "ราชพฤกษ์"
      - "นครอินทร์"

notifications:
  discord:
    enabled: true
    webhook_url: "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL"
```

---

## 🖥️ วิธีการใช้งาน (Usage Modes)

### 1. เปิด Web Dashboard พร้อมแผนที่ Interactive (แนะนำ)
```bash
python -m nummailai web --port 8080
```
เปิดเบราว์เซอร์ไปที่: **`http://localhost:8080`**
- คลิกบนแผนที่เพื่อย้ายพิกัดบ้าน
- เลื่อน Slider ปรับระยะทางรัศมี (กม.)
- เพิ่มคำค้นหาและทดสอบส่ง Discord ได้ทันที

---

### 2. ตรวจสอบข้อมูลทันที 1 ครั้ง (Single Run / Cron)
```bash
python -m nummailai check
```
*(หากต้องการทดสอบการจับคู่โดยไม่ส่ง Discord จริง ให้ใส่ `--dry-run`)*
```bash
python -m nummailai check --dry-run
```

---

### 3. รันเป็น Daemon ตรวจสอบอัตโนมัติตลอด 24 ชม.
```bash
python -m nummailai daemon --interval 15
```
*(ตรวจสอบข้อมูลใหม่ทุก ๆ 15 นาที)*

---

### 4. ดูรายการเหตุน้ำไม่ไหลทั้งหมดบน Terminal
```bash
python -m nummailai list -n 10
```

---

### 5. ทดสอบส่งข้อความไปยัง Discord Webhook
```bash
python -m nummailai test-discord
# หรือระบุ URL ตรงๆ
python -m nummailai test-discord --url "https://discord.com/api/webhooks/..."
```

---

## 🔔 วิธีสร้าง Discord Webhook

1. ใน Discord Server ของคุณ ไปที่ **Server Settings** > **Integrations** > **Webhooks**
2. คลิก **New Webhook**
3. เลือก Channel ที่ต้องการให้บอทแจ้งเตือน
4. คลิก **Copy Webhook URL**
5. นำ URL มาวางใน `config.yaml` หรือกรอกผ่านหน้า Web Dashboard

---

## 🤖 ตั้งค่ารัน 24/7 บน Linux (Systemd Service)

1. คัดลอกไฟล์ service ไปยัง systemd:
```bash
sudo cp systemd/nummailai.service /etc/systemd/system/nummailai.service
sudo systemctl daemon-reload
sudo systemctl enable --now nummailai
```
2. ตรวจสอบสถานะการทำงาน:
```bash
sudo systemctl status nummailai
```

---

## 🐳 รันด้วย Docker

```bash
# Build Docker Image
docker build -t nummailai .

# Run Container
docker run -d -p 8080:8080 -v $(pwd)/config.yaml:/app/config.yaml -v $(pwd)/data:/app/data --name nummailai nummailai
```

---

## 🧪 การรันชุดทดสอบ (Unit Tests)

```bash
python -m unittest discover tests
```

---

## 📄 License
MIT License - สามารถนำไปปรับแต่งและใช้งานได้ฟรี
