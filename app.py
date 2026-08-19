from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import pickle
import numpy as np
import requests
import sqlite3
import hashlib
from datetime import datetime
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Check parent directory or AWS Lambda task root if running in serverless subfolder
if not os.path.exists(os.path.join(BASE_DIR, 'best.pkl')):
    parent_dir = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))
    if os.path.exists(os.path.join(parent_dir, 'best.pkl')):
        BASE_DIR = parent_dir
    else:
        task_root = os.environ.get('LAMBDA_TASK_ROOT', '')
        if task_root and os.path.exists(os.path.join(task_root, 'best.pkl')):
            BASE_DIR = task_root

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.secret_key = os.environ.get('SECRET_KEY', 'aplysia-secret-key-change-in-production')

# ─── Load ML Model ────────────────────────────────────────────
MODEL_PATH = os.path.join(BASE_DIR, 'best.pkl')

with open(MODEL_PATH, 'rb') as f:
    bundle = pickle.load(f)

model = bundle['model']
scaler = bundle['scaler']
le = bundle['label_encoder']
feat_names = bundle['features']
model_name = bundle['model_name']
model_acc = bundle['accuracy']

# ─── Database Configuration ───────────────────────────────────
# Use /tmp on serverless environments where local filesystem is read-only
if os.environ.get('NETLIFY') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('VERCEL'):
    DATABASE = '/tmp/apllysia.db'
else:
    DATABASE = os.path.join(BASE_DIR, 'instance', 'apllysia.db')

def get_db():
    """Get database connection with auto-init for ephemeral filesystems"""
    db_dir = os.path.dirname(DATABASE)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except OSError:
            pass
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn

def init_db():
    """Initialize database with tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Predictions history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            heartbeat REAL,
            emg REAL,
            spo2 REAL,
            blood_pressure REAL,
            prediction TEXT,
            confidence REAL,
            recommendation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# ─── Helper Functions ─────────────────────────────────────────
def hash_password(password):
    """Hash password securely using Werkzeug (salted)"""
    return generate_password_hash(password)

def verify_password(password, hashed):
    """Verify password with support for Werkzeug hash and legacy sha256"""
    if hashed.startswith('scrypt:') or hashed.startswith('pbkdf2:') or hashed.startswith('argon2:'):
        return check_password_hash(hashed, password)
    return hashlib.sha256(password.encode()).hexdigest() == hashed

def predict_seizure(heartbeat, emg, spo2, bp):
    """Make prediction using the loaded model"""
    input_arr = np.array([[heartbeat, emg, spo2, bp]])
    input_scaled = scaler.transform(input_arr)
    
    pred_enc = model.predict(input_scaled)[0]
    pred_label = le.inverse_transform([pred_enc])[0]
    
    confidence = 0.0
    if hasattr(model, 'predict_proba'):
        try:
            probas = model.predict_proba(input_scaled)[0]
            confidence = float(probas[pred_enc] * 100)
        except Exception:
            confidence = 0.0
    
    if confidence == 0.0 and hasattr(model, 'decision_function'):
        try:
            df = model.decision_function(input_scaled)
            scores = df[0] if df.ndim > 1 else df
            if np.ndim(scores) == 0:
                score = float(scores)
                prob = 1.0 / (1.0 + np.exp(-score))
                confidence = float(prob * 100 if pred_enc == 1 else (1.0 - prob) * 100)
            else:
                exp_scores = np.exp(scores - np.max(scores))
                softmax_probs = exp_scores / np.sum(exp_scores)
                confidence = float(softmax_probs[pred_enc] * 100)
        except Exception:
            confidence = 95.0
    
    # Generate recommendation based on prediction
    recommendations = {
        'no epileptic': {
            'title': '✅ Low Risk - Maintain Healthy Habits',
            'details': [
                'Continue regular monitoring of vitals',
                'Maintain proper sleep schedule (7-8 hours)',
                'Stay hydrated and follow balanced diet',
                'Regular exercise to maintain cardiovascular health',
                'Follow up with doctor annually'
            ]
        },
        'early prediction': {
            'title': '⚠️ Early Warning Signs Detected',
            'details': [
                'Consult with neurologist within 1 week',
                'Keep a seizure diary noting any unusual sensations',
                'Avoid triggers like lack of sleep, stress, alcohol',
                'Ensure someone is aware of your condition',
                'Consider wearing medical alert jewelry',
                'Download seizure tracking app for monitoring'
            ]
        },
        'epileptic': {
            'title': '🔴 URGENT - High Risk Seizure Activity',
            'details': [
                'SEEK IMMEDIATE MEDICAL ATTENTION',
                'Contact your neurologist or go to ER',
                'Do not drive or operate machinery',
                'Ensure you are in a safe environment',
                'Have someone stay with you',
                'Take prescribed medications as directed',
                'Emergency Contact: Call 911 or local emergency services'
            ]
        }
    }
    
    rec = recommendations.get(pred_label, recommendations['no epileptic'])
    
    return {
        'prediction': pred_label,
        'confidence': confidence,
        'recommendation_title': rec['title'],
        'recommendation_details': rec['details']
    }

def save_prediction(user_id, data, prediction_result):
    """Save prediction to database"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO predictions (user_id, heartbeat, emg, spo2, blood_pressure, 
                                 prediction, confidence, recommendation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        data['heartbeat'],
        data['emg'],
        data['spo2'],
        data['bloodpressure'],
        prediction_result['prediction'],
        prediction_result['confidence'],
        prediction_result['recommendation_title']
    ))
    conn.commit()
    prediction_id = cursor.lastrowid
    conn.close()
    return prediction_id

# ─── Routes ────────────────────────────────────────────────────
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = hash_password(password)
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                         (username, email, hashed_password))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists!', 'danger')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and verify_password(password, user['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """User dashboard with prediction history"""
    if 'user_id' not in session:
        flash('Please login to access dashboard.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM predictions 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (session['user_id'],))
    predictions = cursor.fetchall()
    conn.close()
    
    return render_template('dashboard.html', predictions=predictions)

@app.route('/delete_prediction/<int:pred_id>', methods=['GET', 'POST'])
def delete_prediction(pred_id):
    """Delete a prediction from history"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM predictions WHERE id = ? AND user_id = ?',
                  (pred_id, session['user_id']))
    conn.commit()
    conn.close()
    
    flash('Prediction deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/view_prediction/<int:pred_id>')
def view_prediction(pred_id):
    """View detailed prediction"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM predictions 
        WHERE id = ? AND user_id = ?
    ''', (pred_id, session['user_id']))
    prediction = cursor.fetchone()
    conn.close()
    
    if prediction:
        return render_template('view_prediction.html', prediction=prediction)
    else:
        flash('Prediction not found.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/predict')
def predict():
    """Prediction page for vital inputs"""
    if 'user_id' not in session:
        flash('Please login to make predictions.', 'warning')
        return redirect(url_for('login'))
    
    default_data = {
        'heartbeat': '85',
        'emg': '50',
        'spo2': '98',
        'bloodpressure': '120'
    }
    return render_template('predict.html', data=default_data)

@app.route('/predict_submit', methods=['POST'])
def predict_submit():
    """Process prediction"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Robust parsing for input fields (handles string fractions like 120/80)
        raw_hb = str(request.form.get('heartbeat', '85')).strip()
        raw_emg = str(request.form.get('emg', '500')).strip()
        raw_spo2 = str(request.form.get('spo2', '98')).strip()
        raw_bp = str(request.form.get('bloodpressure', '120')).strip().split('/')[0].strip()

        hb = float(raw_hb)
        emg = float(raw_emg)
        spo2 = float(raw_spo2)
        bp = float(raw_bp)

        # Range checks (min, max)
        if not (30 <= hb <= 220):
            flash('Heartbeat must be between 30 and 220 BPM.', 'danger')
            return redirect(url_for('predict'))
        if not (0 <= emg <= 1024):
            flash('EMG value must be between 0 and 1024.', 'danger')
            return redirect(url_for('predict'))
        if not (50 <= spo2 <= 100):
            flash('SpO2 must be between 50% and 100%.', 'danger')
            return redirect(url_for('predict'))
        if not (50 <= bp <= 250):
            flash('Blood pressure must be between 50 and 250 mmHg.', 'danger')
            return redirect(url_for('predict'))

        data = {
            'heartbeat': hb,
            'emg': emg,
            'spo2': spo2,
            'bloodpressure': bp
        }
        
        # Make prediction
        prediction_result = predict_seizure(
            data['heartbeat'],
            data['emg'],
            data['spo2'],
            data['bloodpressure']
        )
        
        # Save to database
        pred_id = save_prediction(session['user_id'], data, prediction_result)
        
        # Store result in session for result page
        session['last_prediction'] = {
            'data': data,
            'result': prediction_result,
            'pred_id': pred_id
        }
        
        return redirect(url_for('result'))
        
    except Exception as e:
        flash(f'Error making prediction: {str(e)}', 'danger')
        return redirect(url_for('predict'))

@app.route('/result')
def result():
    """Display prediction result"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if 'last_prediction' not in session:
        flash('No prediction to display.', 'warning')
        return redirect(url_for('predict'))
    
    prediction = session['last_prediction']
    return render_template('result.html', prediction=prediction)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)