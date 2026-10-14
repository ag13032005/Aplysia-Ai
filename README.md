# 🧠 Aplysia AI - Advanced Epileptic Seizure Detection System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Flask-green.svg)](https://flask.palletsprojects.com/)
[![Machine Learning](https://img.shields.io/badge/ML-Scikit--Learn-orange.svg)](https://scikit-learn.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**Aplysia AI** is a machine learning-powered web platform designed to analyze real-time patient physiological vitals and predict the risk of epileptic seizure activity with high accuracy and actionable clinical recommendations.

---

## 🚀 Key Features

- **⚡ Instant AI Prediction**: Powered by a trained Support Vector Classification (SVC) model that evaluates key neurological and cardiovascular biomarkers.
- **🛡️ Real-Time Range Locking & Visual Safety**:
  - Live client-side input validation.
  - Interactive **glowing red box animations** and instant warning messages for out-of-range physiological values.
- **🔒 Secure Authentication System**:
  - User registration and login protected with salted password hashing (`werkzeug.security`).
  - Session-based user authentication.
- **📊 Prediction History Dashboard**:
  - Comprehensive dashboard tracking historical predictions, vitals, confidence scores, and date/time stamps.
  - Detailed report view and one-click printable medical summaries.
- **💡 Actionable Medical Guidance**:
  - Automatically generates customized clinical advice based on risk level (Low Risk, Early Warning, High Risk / Epileptic).
- **📡 ThingSpeak Sensor Import**:
  - The prediction form can fetch the latest reading from channel `3347782`.
  - ThingSpeak fields map to `field1` heartbeat, `field2` EMG, `field3` SpO₂, and `field4` systolic blood pressure.

---

## 📈 Supported Vital Biomarkers

| Vital Metric | Allowed Range | Reference Normal Range | Description |
| :--- | :--- | :--- | :--- |
| **Heartbeat (BPM)** | `30 – 220 BPM` | `60 – 100 BPM` | Patient heart rate per minute |
| **EMG Value** | `0 – 1024` | `0 – 500` | Electromyography muscle signal intensity |
| **$\text{SpO}_2$ (%)** | `50% – 100%` | `95% – 100%` | Blood oxygen saturation percentage |
| **Blood Pressure (mmHg)** | `50 – 250 mmHg` | `90 – 120 mmHg` | Systolic arterial blood pressure |

---

## 🛠️ Technology Stack

- **Backend**: Python, Flask, SQLite3, Werkzeug
- **Machine Learning**: Scikit-Learn, NumPy, Pickle
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, FontAwesome
- **Deployment**: Gunicorn, Render-ready, Serverless WSGI support

---

## 💻 Local Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/ag13032005/Aplysia-Ai.git
cd Aplysia-Ai
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

For deployment, set `THINGSPEAK_URL` and `THINGSPEAK_API_KEY` environment variables to override the default channel configuration.

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🌐 Cloud Deployment (Render.com)

1. Create a new **Web Service** on [Render.com](https://render.com).
2. Connect your GitHub repository: `ag13032005/Aplysia-Ai`.
3. Set the following build settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Click **Create Web Service**.

---

## 📁 Project Structure

```
Aplysia-Ai/
├── BACKEND/
│   ├── epileptic_seizure_prediction_dataset.csv
│   └── epileptic_seizure_prediction.ipynb
├── instance/
│   └── apllysia.db
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── index.html
│   ├── login.html
│   ├── predict.html
│   ├── register.html
│   ├── result.html
│   └── view_prediction.html
├── app.py
├── best.pkl
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 📄 License
This project is licensed under the MIT License.
