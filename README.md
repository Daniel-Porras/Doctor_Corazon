# 🫀 Dr Corazón - Real-Time ECG Monitoring System with AI

**End-to-end system for ECG capture, automatic diagnosis, and real-time visualization using deep learning.**

<p align="center">
  <img src="https://img.shields.io/badge/Hardware-ESP32%20%2B%20ADS1293-blue" />
  <img src="https://img.shields.io/badge/AI-TensorFlow%20CNN-red" />
  <img src="https://img.shields.io/badge/Backend-Python%20%2B%20Flask-green" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-blue" />
</p>

---

## 📋 Overview

**Dr Corazón** integrates hardware ECG capture, real-time signal processing, AI-powered automatic diagnosis, and interactive web visualization for cardiac monitoring.

### What it does

```
Patient → Electrodes → ESP32 → WiFi → Server → AI → Dashboard
                                         ↓
                                   Automatic Diagnosis
```

**In 3 steps:**
1. 📡 **Captures**: ESP32 reads ECG signals from ADS1293 at 853 Hz
2. 🤖 **Analyzes**: CNN classifies into 4 categories (Normal, MI, Bradycardia, Tachycardia)
3. 📊 **Displays**: Web dashboard shows real-time diagnosis

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      HARDWARE LAYER                         │
│                                                             │
│  Patient (5 EASI electrodes)                                │
│     ↓                                                       │
│  ADS1293 (3-channel ECG, 24-bit, 853 Hz)                   │
│     ↓ SPI                                                   │
│  ESP32 (capture + WiFi transmission)                        │
│     ↓ WiFi UDP (Port 5005)                                 │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                   PROCESSING LAYER                          │
│                                                             │
│  receiver_udp.py → Signal processing (filter, resample)     │
│     ↓                                                       │
│  holter_ai.py → CNN diagnosis (TensorFlow)                  │
│     ↓                                                       │
│  hr_hrv_analyzer.py → HR/HRV metrics                        │
│     ↓                                                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                         │
│                                                             │
│  app_supabase_auth_v2.py (Flask + WebSocket)               │
│     ↓                                                       │
│  PostgreSQL/Supabase (data persistence)                     │
│     ↓                                                       │
│  Web Dashboard (real-time visualization)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

### Medical Users
- ✅ Real-time monitoring (10-second updates)
- ✅ Automatic diagnosis (92% accuracy)
- ✅ Critical alerts (MI detection)
- ✅ Multi-patient management
- ✅ Complete history tracking
- ✅ HR/HRV metrics (SDNN, RMSSD, pNN50)

### Developers
- ✅ Open source & modular
- ✅ REST API + WebSocket
- ✅ Multi-user with Row Level Security
- ✅ Comprehensive documentation
- ✅ Easy to extend

### Technical
- ✅ High frequency: 853 Hz/channel
- ✅ Low latency: < 3 seconds end-to-end
- ✅ Secure: Authentication + RLS + HTTPS ready
- ✅ Robust: Error handling, auto-reconnection

---

## 🛠️ Technology Stack

### Hardware
- **MCU**: ESP32 (dual-core @ 240 MHz)
- **ADC**: ADS1293 (24-bit, 3 channels)
- **Communication**: WiFi 802.11 b/g/n

### Backend
- **Language**: Python 3.8+
- **Framework**: Flask 2.3.0
- **AI/ML**: TensorFlow 2.13.0
- **Signal Processing**: NumPy, SciPy
- **Database**: PostgreSQL (Supabase)
- **Real-time**: Flask-SocketIO

### Frontend
- **UI**: HTML5, CSS3, JavaScript
- **Charts**: Plotly.js
- **Real-time**: Socket.IO client

---

## 💻 System Requirements

### Hardware
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **PC** | 2 cores, 4GB RAM, 10GB disk | 4 cores, 8GB RAM, 20GB SSD |
| **ESP32** | ESP32 DevKit, 4MB Flash | ESP32-WROVER, 8MB Flash |
| **ADS1293** | ADS1293IPBS | - |
| **Electrodes** | 5 disposable Ag/AgCl | - |

### Software
- **OS**: Windows 10+, macOS 10.15+, Linux (Ubuntu 20.04+)
- **Python**: 3.8 - 3.11
- **ESP-IDF**: 4.4+
- **Browser**: Chrome 90+, Firefox 88+

### Cloud Services
- **Supabase** account (free tier available)

---

## 📥 Quick Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-username/dr-corazon.git
cd dr-corazon
```

### 2. Setup Backend

```bash
cd backend/
python -m venv .env
source .env/bin/activate  # Windows: .env\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

Create `.env` file:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
FLASK_SECRET_KEY=your-secret-key
MODEL_PATH=vcg_model_optimized_4classes.h5
UDP_PORT=5005
```

### 4. Setup Database

1. Create Supabase account: https://supabase.com
2. Create new project
3. Run SQL from `database/schema.sql` in SQL Editor

### 5. Create Admin User

```bash
python crear_admin.py
```

### 6. Configure ESP32 Firmware

Edit `firmware/esp32-ads1293/main/main.c`:

```c
#define WIFI_SSID      "YourSSID"
#define WIFI_PASS      "YourPassword"
#define UDP_DEST_IP    "192.168.1.100"  // Your PC IP
```

### 7. Compile and Flash ESP32

```bash
cd firmware/esp32-ads1293/
idf.py build
idf.py -p /dev/ttyUSB0 flash
```

---

## 🚀 Quick Start

### 1. Start Server

```bash
cd backend/
source .env/bin/activate
python app_supabase_auth_v2.py
```

Expected output:
```
🫀 Dr Corazón - ECG Monitoring System
✓ Supabase connected
✓ AI model loaded (4 classes)
✓ Server running on http://0.0.0.0:5000
```

### 2. Access Dashboard

1. Open browser: `http://localhost:5000`
2. Login with admin credentials
3. Create patient
4. Select patient
5. Place electrodes on patient
6. System automatically captures and analyzes

---

## 📌 Hardware Connections

### ESP32 ↔ ADS1293

| ESP32 Pin | ADS1293 Pin | Function |
|-----------|-------------|----------|
| GPIO 23 | DIN | SPI MOSI |
| GPIO 19 | DOUT | SPI MISO |
| GPIO 18 | SCLK | SPI Clock |
| GPIO 5 | CS | Chip Select |
| GPIO 27 | DRDYB | Data Ready Interrupt |
| GPIO 26 | ALAB | Lead-off Detection |
| GND | GND | Ground |
| 3.3V | AVDD/DVDD | Power |

### Electrodes ↔ ADS1293 (EASI System)

| Electrode | Body Position | ADS1293 Pin |
|-----------|--------------|-------------|
| E | Sternum (manubrium) | IN1 |
| A | Xiphoid process | IN2 |
| S | Right upper back | RLD |
| I | Left mid-axillary (5th ICS) | IN3 |
| V | V2 precordial position | IN4 |

---

## 🔄 Data Flow (End-to-End)

```
t=0.000s  Heart beats → electrical signal
t=0.001s  Electrodes capture signal
t=0.002s  ADS1293 converts analog → digital (24-bit)
t=0.003s  ESP32 reads via SPI
t=0.004s  ESP32 sends via WiFi UDP
t=0.010s  PC receives packet
t=10.00s  Complete 10-second window processed
t=10.20s  CNN executes inference → diagnosis
t=10.30s  HR/HRV calculated
t=10.50s  WebSocket emits to dashboard
t=10.55s  Dashboard updates

TOTAL LATENCY: ~10.5 seconds (10s window + 0.5s processing)
```

---

## 🧩 Main Components

### 1. ESP32 Firmware (`firmware/`)
- **Function**: ECG signal capture and WiFi transmission
- **Language**: C (ESP-IDF)
- **Features**: 2 FreeRTOS tasks, anti-bounce interrupts, UDP packet batching

### 2. UDP Receiver (`receiver_udp.py`)
- **Function**: Signal processing
- **Features**: Bandpass filter (0.5-40 Hz), notch filter (60 Hz), EASI→XYZ transformation

### 3. AI Engine (`holter_ai.py`)
- **Function**: Automatic diagnosis
- **Model**: CNN with 2.8M parameters
- **Accuracy**: 92%
- **Classes**: Normal, MI, Bradycardia, Tachycardia

### 4. HR/HRV Analyzer (`hr_hrv_analyzer.py`)
- **Function**: Cardiac metrics
- **Output**: HR (BPM), SDNN, RMSSD, pNN50

### 5. Flask Server (`app_supabase_auth_v2.py`)
- **Function**: System orchestration
- **Features**: REST API, WebSocket, multi-threading, authentication

### 6. PostgreSQL Database (Supabase)
- **Tables**: user_profiles, pacientes, diagnosticos
- **Security**: Row Level Security (RLS)

### 7. Web Dashboard (`templates/`)
- **Pages**: Login, Dashboard, Admin Panel
- **Features**: Real-time charts (Plotly.js), WebSocket updates

---

## 📊 Performance Metrics

```
Sampling rate:          853 Hz/channel
Resolution:             24 bits
Channels:               3 simultaneous
Throughput:             ~61 KB/s (raw data)
End-to-end latency:     < 11 seconds
Packet loss:            < 0.01% (good WiFi)
CPU usage:              ~15% @ 240 MHz
AI inference time:      ~100 ms
```

---

## 📚 Use Cases

### 1. Hospital Monitoring
- **Scenario**: 10 ICU patients with continuous monitoring
- **Benefits**: 24/7 monitoring, automatic alerts, centralized supervision

### 2. Telemedicine
- **Scenario**: Patient at home with portable device
- **Benefits**: Remote care, proactive monitoring, reduced ER visits

### 3. Medical Research
- **Scenario**: Clinical study with 100 subjects over 1 month
- **Benefits**: Automated data collection, large datasets, statistical analysis

### 4. Medical Education
- **Scenario**: University ECG interpretation training
- **Benefits**: Real cases, immediate feedback, safe practice

---

## 📖 Documentation

| Document | Audience | Content |
|----------|----------|---------|
| `README.md` | Everyone | Project overview (this file) |
| `README_ESP32.md` | Embedded developers | ESP32 firmware details |
| `GUIA_CONCEPTUAL.md` | Non-technical | Concepts with analogies (Spanish) |
| `GUIA_TECNICA_INGENIEROS.md` | Engineering students | Technical fundamentals (Spanish) |
| `PRESENTACION_TECNICA.md` | Technical audience | Complete specifications (Spanish) |

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -m 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Open Pull Request

### Areas of Contribution
- **Development**: New features, optimizations, bug fixes
- **Documentation**: Improve READMEs, translations, tutorials
- **Research**: New algorithms, clinical validation, datasets
- **Design**: UI/UX improvements, icons, accessibility

---

## 📄 License & Legal

### Academic and Medical License

This project is licensed for:
- ✅ Academic and educational use
- ✅ Medical research
- ✅ Development and testing
- ✅ Prototypes and demos

### Restrictions

❌ **DO NOT USE IN MEDICAL PRODUCTION** without:
1. Complete clinical validation
2. Regulatory approvals (FDA, CE, INVIMA, etc.)
3. Medical device certification
4. Liability insurance
5. Compliance with standards (IEC 60601, ISO 13485, HIPAA, GDPR)

### Disclaimer

**⚠️ IMPORTANT WARNING:**

This system is a **research prototype**. Automatic diagnoses are **informative** and **DO NOT replace** professional medical judgment.

**Authors are NOT responsible for:**
- Incorrect diagnoses
- Clinical decisions based on the system
- Patient or equipment damage
- Data loss
- System malfunction

**Use at your own risk.**

---

## 👥 Team & Contact

### Technical Support
- **GitHub Issues**: https://github.com/your-username/dr-corazon/issues
- **Email**: support@drcorazon.com

### Collaboration
- **Email**: collaboration@drcorazon.com

---

## 🔗 Useful Links

### Technical Documentation
- **ESP-IDF**: https://docs.espressif.com/projects/esp-idf/
- **Flask**: https://flask.palletsprojects.com/
- **TensorFlow**: https://www.tensorflow.org/
- **Supabase**: https://supabase.com/docs

### Datasheets
- **ADS1293**: https://www.ti.com/product/ADS1293
- **ESP32**: https://www.espressif.com/en/products/socs/esp32

### Standards
- **IEC 60601**: Medical device safety
- **HL7 FHIR**: Healthcare interoperability
- **ISO 13485**: Medical device quality management

---

## 📊 Project Stats

```
Lines of code:      ~15,000
Files:              45+
Commits:            500+
Contributors:       4
Issues resolved:    120+
Pull requests:      85+
```

---

**🫀 Dr Corazón - Real-Time ECG Monitoring System with AI**

*Developed with ❤️ to save lives*

---

**Last updated:** December 2024  
**Version:** 2.0  
**Build:** Stable

---
