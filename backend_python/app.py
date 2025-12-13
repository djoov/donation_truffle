from flask import Flask, render_template, request, redirect, url_for, session, flash
from web3 import Web3
import sqlite3
import os
import re
import json
import time
from datetime import datetime, timedelta
import feedparser
from time import mktime

# --- KONFIGURASI ---
app = Flask(__name__)
app.secret_key = 'rahasia_donasi_blockchain'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# --- CONFIG EMAIL (GMAIL) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'jouvialdalopezgamandi@gmail.com'
app.config['MAIL_PASSWORD'] = 'flkx busl pzmr fnxu' 

# Imports untuk Email
import smtplib
from email.mime.text import MIMEText
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer

# Import Contract Data
try:
    from contract_data import contract, web3
except ImportError:
    contract = None
    web3 = None
    print("Warning: contract_data.py tidak ditemukan. Fitur blockchain tidak aktif.")

# --- 1. CONTEXT PROCESSOR (SMART CACHING) ---
# Cache sederhana untuk mengurangi beban request ke Ganache
CACHE_BC = {
    'last_updated': 0,
    'data': {
        'connected': False,
        'gas_price': '0',
        'block_number': '0'
    }
}
CACHE_DURATION = 5 # Update setiap 5 detik

@app.context_processor
def inject_blockchain_status():
    global CACHE_BC
    current_time = time.time()
    
    # 1. Update Global Stats (Gas, Block, Status) jika Cache Expired
    if current_time - CACHE_BC['last_updated'] > CACHE_DURATION:
        try:
            if web3 and web3.is_connected():
                CACHE_BC['data']['connected'] = True
                CACHE_BC['data']['block_number'] = web3.eth.block_number
                gas_wei = web3.eth.gas_price
                CACHE_BC['data']['gas_price'] = "{:.1f}".format(web3.from_wei(gas_wei, 'gwei'))
            else:
                CACHE_BC['data']['connected'] = False
        except:
            CACHE_BC['data']['connected'] = False
        
        CACHE_BC['last_updated'] = current_time

    # Salin data dari cache
    status = CACHE_BC['data'].copy()
    status['user_balance'] = '0.0000'

    # 2. Update User Balance (Real-time per request, tapi hanya jika login)
    # Balance user penting untuk validasi, jadi fetch real-time (bisa di-optimize nanti jika perlu)
    if 'wallet' in session and status['connected']:
        try:
            bal_wei = web3.eth.get_balance(session['wallet'])
            bal_eth = web3.from_wei(bal_wei, 'ether')
            status['user_balance'] = "{:.4f}".format(float(bal_eth))
        except:
            status['user_balance'] = "Err"

    return dict(bc_stat=status)

# --- 2. DATABASE SETUP (DIPERBARUI) ---
def init_db():
    if not os.path.exists('instance'):
        os.makedirs('instance')
        
    conn = sqlite3.connect('instance/users.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, 
                  username TEXT, email TEXT, password TEXT, role TEXT, 
                  wallet_address TEXT, private_key TEXT,
                  profile_pic TEXT, bio TEXT, last_username_change TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS campaign_details 
                 (id INTEGER PRIMARY KEY, 
                  blockchain_id INTEGER, 
                  category TEXT, 
                  usage_plan TEXT, 
                  social_link TEXT,
                  tagline TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS campaign_updates 
                 (id INTEGER PRIMARY KEY, blockchain_id INTEGER, 
                  title TEXT, content TEXT, image TEXT, created_at TEXT)''')

    # UPDATE: Menambahkan kolom tx_hash dan nonce
    c.execute('''CREATE TABLE IF NOT EXISTS donations 
                 (id INTEGER PRIMARY KEY, blockchain_id INTEGER, 
                  donor_name TEXT, amount REAL, message TEXT, timestamp TEXT,
                  tx_hash TEXT, nonce INTEGER)''')
    
    # NEW: Security Logs Table
    c.execute('''CREATE TABLE IF NOT EXISTS security_logs 
                 (id INTEGER PRIMARY KEY, timestamp TEXT, ip_address TEXT, 
                  action TEXT, status TEXT, description TEXT, user_id INTEGER)''')
    
    c.execute("SELECT * FROM users WHERE role='admin'")
    if not c.fetchone():
        try:
            admin_wallet = web3.eth.accounts[0] if web3 and web3.is_connected() else "0x0000000000000000000000000000000000000000"
        except:
            admin_wallet = "0x0000000000000000000000000000000000000000"
            
        c.execute("INSERT INTO users (username, email, password, role, wallet_address, private_key, profile_pic) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  ('SuperAdmin', 'admin@donasi.com', 'admin123', 'admin', admin_wallet, 'ADMIN_KEY', 'default_user.png'))
    
    conn.commit()
    conn.close()

init_db()

# --- 3. HELPER FUNCTIONS ---
def get_db_connection():
    conn = sqlite3.connect('instance/users.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_username_by_wallet(wallet_addr):
    conn = get_db_connection()
    user = conn.execute('SELECT username FROM users WHERE wallet_address = ?', (wallet_addr,)).fetchone()
    conn.close()
    if user:
        return f"{user['username']}"
    return "Unknown User"

def get_all_transactions():
    logs = []
    try:
        if contract:
            # Ambil Event Donasi
            events = contract.events.DonationReceived().get_logs(fromBlock=0)
            for e in events:
                args = e['args']
                tx_hash = e['transactionHash'].hex()
                
                # UPDATE: Ambil Nonce Live dari Blockchain untuk Admin
                nonce_val = "N/A"
                try:
                    tx_detail = web3.eth.get_transaction(tx_hash)
                    nonce_val = tx_detail['nonce']
                except:
                    pass

                logs.append({
                    'type': 'Donasi Masuk',
                    'campaign_id': args['campaignId'],
                    'from': get_username_by_wallet(args['donor']),
                    'from_addr': args['donor'],
                    'amount': web3.from_wei(args['amount'], 'ether'),
                    'timestamp': time.ctime(args['timestamp']),
                    'tx_hash': tx_hash,
                    'nonce': nonce_val
                })
            
            # Ambil Event Campaign Created
            events_created = contract.events.CampaignCreated().get_logs(fromBlock=0)
            for e in events_created:
                args = e['args']
                tx_hash = e['transactionHash'].hex()
                
                nonce_val = "N/A"
                try:
                    tx_detail = web3.eth.get_transaction(tx_hash)
                    nonce_val = tx_detail['nonce']
                except:
                    pass

                logs.append({
                    'type': 'Campaign Dibuat',
                    'campaign_id': args['id'],
                    'from': get_username_by_wallet(args['creator']),
                    'from_addr': args['creator'],
                    'amount': '-',
                    'timestamp': time.ctime(args['timestamp']),
                    'tx_hash': tx_hash,
                    'nonce': nonce_val
                })
            logs.sort(key=lambda x: x['timestamp'], reverse=True)
    except Exception as e:
        print(f"Error fetching logs: {e}")
    return logs

def cleanhtml(raw_html):
    """Menghapus tag HTML (seperti <img>, <div>) dari teks"""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

# --- 3b. SECURITY LOGGING HELPER & WAF ---
# In-memory storage for Rate Limiting (Reset on restart)
# Format: { 'ip_address': [timestamp1, timestamp2, ...] }
login_attempts = {}

def check_rate_limit(ip_addr, limit=5, window=600):
    """
    Return True if IP is blocked (too many attempts in window seconds).
    Clean up old timestamps.
    """
    now = time.time()
    if ip_addr not in login_attempts:
        login_attempts[ip_addr] = []
    
    # Filter attempts within window
    login_attempts[ip_addr] = [t for t in login_attempts[ip_addr] if now - t < window]
    
    if len(login_attempts[ip_addr]) >= limit:
        return True
    return False

def record_failed_attempt(ip_addr):
    if ip_addr not in login_attempts:
        login_attempts[ip_addr] = []
    login_attempts[ip_addr].append(time.time())

def detect_suspicious_input(input_str):
    """
    Basic WAF: Returns (True, Type) if suspicious pattern found.
    """
    if not input_str: return False, None
    input_str = str(input_str).lower()
    
    # SQL Injection Patterns
    sqli_patterns = ["union select", "' or 1=1", "--", "; drop table", "information_schema"]
    for pat in sqli_patterns:
        if pat in input_str: return True, "SQL Injection Attempt"
    
    # XSS Patterns
    xss_patterns = ["<script>", "javascript:", "onload=", "onerror="]
    for pat in xss_patterns:
        if pat in input_str: return True, "XSS/Script Attempt"
        
    return False, None

def log_security(action, status, description, user_id=None):
    """
    Mencatat aktivitas keamanan ke database.
    Status: 'low' (Info), 'medium' (Warning), 'high' (Critical/Error)
    Added: User-Agent logging in description.
    """
    try:
        if not user_id and 'user_id' in session:
            user_id = session['user_id']
        
        ip_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
        ua = request.user_agent.string if request.user_agent else "Unknown"
        
        # Append UA to description
        full_desc = f"{description} [UA: {ua}]"
        
        conn = get_db_connection()
        conn.execute('INSERT INTO security_logs (timestamp, ip_address, action, status, description, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                     (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip_addr, action, status, full_desc, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log security event: {e}")

# --- FUNGSI FETCH BERITA (MULTI-SOURCE AGGREGATOR) ---
def get_humanitarian_news():
    rss_sources = [
        {"url": "https://www.antaranews.com/rss/humaniora.xml", "name": "ANTARA NEWS"},
        {"url": "https://www.cnnindonesia.com/nasional/rss", "name": "CNN INDONESIA"},
        {"url": "https://www.republika.co.id/rss/nasional/umum", "name": "REPUBLIKA"},
        {"url": "https://www.viva.co.id/rss/berita/nasional", "name": "VIVA NEWS"}
    ]
    keywords = ["banjir", "gempa", "longsor", "kebakaran", "bencana", "tsunami", "korban", "bantuan", "donasi", "miskin", "sosial", "kemanusiaan"]
    aggregated_news = []
    
    for source in rss_sources:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:5]: # Ambil 5 berita per sumber untuk di-filter
                title = entry.title.lower()
                raw_summary = entry.summary if hasattr(entry, 'summary') else ""
                
                if any(k in title for k in keywords) or any(k in raw_summary.lower() for k in keywords):
                    # 1. Bersihkan HTML Tags DULU
                    clean_summary = cleanhtml(raw_summary)
                    
                    # 2. Potong teks agar tidak kepanjangan
                    final_summary = clean_summary[:100] + "..." if len(clean_summary) > 100 else clean_summary
                    
                    pub_time = entry.published_parsed if hasattr(entry, 'published_parsed') else time.gmtime()
                    timestamp = mktime(pub_time) if pub_time else 0
                    
                    aggregated_news.append({
                        'title': entry.title,
                        'link': entry.link,
                        'published': entry.published if hasattr(entry, 'published') else "Baru saja",
                        'timestamp': timestamp,
                        'summary': final_summary,
                        'source': source["name"]
                    })
        except Exception as e:
            print(f"Error parsing RSS: {e}")
            continue

    aggregated_news.sort(key=lambda x: x['timestamp'], reverse=True)
    final_news = aggregated_news[:4]
        
    if not final_news:
        final_news = [
            {'title': 'Banjir Bandang Terjang Pemukiman Warga', 'link': '#', 'published': 'Hari ini', 'summary': 'Hujan deras menyebabkan tanggul jebol. Warga membutuhkan bantuan logistik...', 'source': 'Simulasi'},
            {'title': 'Gempa M 5.6 Guncang Wilayah Cianjur', 'link': '#', 'published': 'Kemarin', 'summary': 'Gempa darat dangkal menyebabkan kerusakan infrastruktur...', 'source': 'Simulasi'}
        ]
    return final_news


# Validasi dan Helper Lainnya...

# --- 3d. CAMPAIGN NOTIFICATION HELPER ---
def send_campaign_notification(to_email, username, campaign_title, status):
    """
    Kirim email notifikasi status kampanye (Pending / Approved / Rejected)
    Status: 'pending', 'approved', 'rejected'
    """
    try:
        sender_email = app.config['MAIL_USERNAME']
        password = app.config['MAIL_PASSWORD']
        
        # MOCK MODE jika kredensial belum diset
        if 'xxxx' in password:
            print(f"[MOCK CAMPAIGN EMAIL] To: {to_email} | Status: {status} | Title: {campaign_title}")
            return

        msg = MIMEMultipart()
        msg['From'] = f"DonasiKuy Admin &lt;{sender_email}&gt;"
        msg['To'] = to_email
        
        # Subject & Color Coding
        if status == 'pending':
            subject = "⏳ Kampanye Menunggu Persetujuan: " + campaign_title
            color = "#f59e0b" # Amber
            status_text = "Sedang Direview"
            desc = "Kampanye Anda berhasil dibuat dan sedang dalam antrean moderasi oleh Admin."
        elif status == 'approved':
            subject = "✅ Kampanye DITERIMA! Silakan Share: " + campaign_title
            color = "#10b981" # Emerald
            status_text = "Disetujui / Aktif"
            desc = "Selamat! Kampanye Anda telah disetujui dan sekarang dapat menerima donasi dari publik."
        else: # rejected
            subject = "❌ Status Kampanye: " + campaign_title
            color = "#ef4444" # Red
            status_text = "Ditolak / Dihapus"
            desc = "Mohon maaf, kampanye Anda tidak memenuhi syarat atau telah dihapus oleh Admin."

        msg['Subject'] = subject

        body = f"""
        <html>
        <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f3f4f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                <div style="background-color: {color}; padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">Status Kampanye</h1>
                </div>
                <div style="padding: 40px 30px;">
                    <h2 style="color: #1f2937; margin-top: 0;">Halo, {username}! 👋</h2>
                    <p style="font-size: 16px; color: #4b5563;">Berikut adalah update terbaru mengenai kampanye Anda:</p>
                    
                    <div style="background-color: #f9fafb; border-left: 5px solid {color}; padding: 20px; margin: 25px 0; border-radius: 4px;">
                        <h3 style="margin: 0 0 10px 0; color: #111;">{campaign_title}</h3>
                        <span style="background-color: {color}; color: white; padding: 4px 12px; border-radius: 99px; font-size: 14px; font-weight: bold;">{status_text}</span>
                        <p style="margin-top: 15px; margin-bottom: 0; color: #4b5563;">{desc}</p>
                    </div>
                    
                    <p>Terima kasih telah menggunakan DonasiKuy untuk misi kebaikan Anda.</p>
                    
                    <div style="margin-top: 40px; border-top: 1px solid #e5e7eb; padding-top: 20px; text-align: center;">
                        <a href="http://localhost:5000/dashboard" style="display: inline-block; color: {color}; text-decoration: none; font-weight: bold;">Ke Dashboard &rarr;</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        print(f"[EMAIL SUCCESS] Campaign logic ({status}) sent to {to_email}")
    except Exception as e:
        print(f"[EMAIL FAILED] {e}")

# --- 3c. EMAIL NOTIFICATION HELPER ---
def send_welcome_email(to_email, username):
    try:
        sender_email = app.config['MAIL_USERNAME']
        password = app.config['MAIL_PASSWORD']
        
        # Cek jika kredensial masih default/kosong
        if 'xxxx' in password:
            print(f"[MOCK EMAIL] To: {to_email} | Subject: Welcome to DonasiKuy | (Konfigurasi SMTP belum diset)")
            return

        msg = MIMEMultipart()
        msg['From'] = f"DonasiKuy Team <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = "Selamat Datang di Keluarga Besar DonasiKuy! 🌍"

        # HTML Body yang Menarik
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
                <div style="background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">DonasiKuy</h1>
                    <p style="color: rgba(255,255,255,0.8);">Platform Donasi Blockchain #1</p>
                </div>
                <div style="padding: 30px; background-color: #ffffff;">
                    <h2 style="color: #4f46e5;">Halo, {username}! 👋</h2>
                    <p>Terima kasih telah bergabung menjadi bagian dari agen perubahan kebaikan.</p>
                    <p>Di <strong>DonasiKuy</strong>, setiap donasi Anda tercatat secara abadi di Blockchain Ethereum, menjamin transparansi 100% tanpa ada yang ditutup-tutupi.</p>
                    
                    <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4ade80;">
                        <strong>Mulai langkah pertama Anda:</strong><br>
                        Jelajahi kampanye kemanusiaan yang membutuhkan uluran tangan Anda hari ini.
                    </div>
                    
                    <a href="http://localhost:5000/dashboard" style="display: inline-block; background-color: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 50px; font-weight: bold; margin-top: 10px;">Mulai Berdonasi</a>
                </div>
                <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #64748b;">
                    &copy; 2025 DonasiKuy Foundation.<br>
                    Transparency is our currency.
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))

        # Kirim via SMTP GMAIL
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        
        print(f"[EMAIL SUCCESS] Welcome email sent to {to_email}")
    except Exception as e:
        print(f"[EMAIL FAILED] Could not send email to {to_email}: {e}")


# --- 3e. RESET PASSWORD HELPER ---
def send_reset_password_email(to_email, token):
    try:
        sender_email = app.config['MAIL_USERNAME']
        password = app.config['MAIL_PASSWORD']
        reset_link = url_for('reset_password', token=token, _external=True)

        if 'xxxx' in password:
            print(f"[MOCK EMAIL] Reset Link for {to_email}: {reset_link}")
            return

        msg = MIMEMultipart()
        msg['From'] = f"DonasiKuy Security &lt;{sender_email}&gt;"
        msg['To'] = to_email
        msg['Subject'] = "🔒 Reset Password DonasiKuy"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
                <div style="background-color: #f8fafc; padding: 30px; text-align: center; border-bottom: 2px solid #ef4444;">
                    <h2 style="color: #ef4444; margin: 0;">Permintaan Reset Password</h2>
                </div>
                <div style="padding: 30px; background-color: #ffffff;">
                    <p>Halo,</p>
                    <p>Kami menerima permintaan untuk mereset password akun DonasiKuy Anda.</p>
                    <p>Silakan klik tombol di bawah ini untuk membuat password baru (Link berlaku 15 menit):</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" style="background-color: #ef4444; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Reset Password Saya</a>
                    </div>
                    
                    <p style="font-size: 14px; color: #64748b;">Jika Anda tidak merasa meminta reset password, abaikan email ini. Akun Anda tetap aman.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        print(f"[EMAIL SUCCESS] Reset link sent to {to_email}")
    except Exception as e:
        print(f"[EMAIL FAILED] {e}")


# --- 3f. DONOR NOTIFICATION HELPERS ---
def get_donor_emails(campaign_id):
    """Mengambil daftar email unik dari semua donatur di kampanye tertentu."""
    conn = get_db_connection()
    # Ambil nama donatur (asumsi username)
    donors = conn.execute("SELECT DISTINCT donor_name FROM donations WHERE blockchain_id = ?", (campaign_id,)).fetchall()
    emails = []
    for d in donors:
        # Cari email berdasarkan username
        user = conn.execute("SELECT email FROM users WHERE username = ?", (d['donor_name'],)).fetchone()
        if user:
            emails.append(user['email'])
    conn.close()
    return list(set(emails))

def send_update_email(recipients, campaign_title, update_title, content, image_filename=None):
    if not recipients: return
    
    sender_email = app.config['MAIL_USERNAME']
    password = app.config['MAIL_PASSWORD']
    
    # Image URL (Localhost context)
    image_html = ""
    if image_filename:
        img_url = url_for('static', filename='uploads/' + image_filename, _external=True)
        image_html = f'<div style="margin: 20px 0;"><img src="{img_url}" style="max-width: 100%; border-radius: 8px;" alt="Update Image"></div>'

    msg = MIMEMultipart()
    msg['From'] = f"DonasiKuy Updates &lt;{sender_email}&gt;"
    msg['Subject'] = f"🔔 Update Terbaru: {campaign_title}"
    msg['Bcc'] = ", ".join(recipients) # Blind Carbon Copy untuk privasi

    body = f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #3b82f6; padding: 20px; text-align: center; color: white;">
                <h2 style="margin:0;">Kabar Terbaru Kampanye</h2>
                <p style="margin:5px 0 0 0; opacity: 0.9;">{campaign_title}</p>
            </div>
            <div style="padding: 30px; background-color: #fff;">
                <h3 style="color: #1e3a8a; margin-top: 0;">{update_title}</h3>
                <div style="font-size: 16px; line-height: 1.6; color: #4b5563;">
                    {content}
                </div>
                {image_html}
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #f3f4f6; text-align: center; font-size: 12px; color: #9ca3af;">
                    Anda menerima email ini karena telah berdonasi di kampanye ini.<br>
                    DonasiKuy - Platform Kebaikan Blockchain.
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        if 'xxxx' in password:
            print(f"[MOCK EMAIL] To Donors ({len(recipients)}): {update_title}")
            return
            
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(sender_email, password)
        # Send to one recipient in To (admin or dummy) and real list in Bcc
        # But send_message handles Bcc automatically if in headers but not in 'To' arg? 
        # Actually standard SMTP needs list of recipients.
        server.send_message(msg, to_addrs=recipients) 
        server.quit()
        print(f"[EMAIL SUCCESS] Update sent to {len(recipients)} donors.")
    except Exception as e:
        print(f"[EMAIL FAILED] Donor update: {e}")

def send_withdrawal_email(recipients, campaign_title):
    if not recipients: return
    sender_email = app.config['MAIL_USERNAME']
    password = app.config['MAIL_PASSWORD']
    
    msg = MIMEMultipart()
    msg['From'] = f"DonasiKuy Finance &lt;{sender_email}&gt;"
    msg['Subject'] = f"💸 Dana Dicairkan: {campaign_title}"
    msg['Bcc'] = ", ".join(recipients)

    body = f"""
    <html>
    <body style="font-family: sans-serif; color: #333;">
        <div style="border: 1px solid #ddd; padding: 20px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #059669;">Dana Telah Dicairkan</h2>
            <p>Halo Orang Baik,</p>
            <p>Kabar gembira! Dana donasi untuk kampanye <strong>{campaign_title}</strong> telah dicairkan oleh kreator untuk memulai implementasi program kebaikan.</p>
            <p>Terima kasih telah menjadi bagian dari perjalanan ini. Tunggu update selanjutnya ya!</p>
            <br>
            <a href="http://localhost:5000/dashboard" style="color: #3b82f6;">Lihat Kampanye</a>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        if 'xxxx' in password:
            print(f"[MOCK EMAIL] Withdrawal Notif to {len(recipients)} donors")
            return
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg, to_addrs=recipients)
        server.quit()
    except Exception as e:
        print(f"[EMAIL FAILED] Withdrawal notif: {e}")

# --- 4. ROUTES UTAMA ---

@app.route('/')
def index():
    latest_news = get_humanitarian_news()
    return render_template('index.html', news=latest_news)

@app.route('/help')
def help_page(): return render_template('help.html')

@app.route('/privacy')
def privacy_page(): return render_template('privacy.html')

@app.route('/how-it-works')
def how_it_works_page(): return render_template('how_it_works.html')

# --- 5. ROUTES AUTH ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']; password = request.form['password']
        ip_addr = request.remote_addr

        # 1. Check Rate Limit
        if check_rate_limit(ip_addr):
            log_security('Rate Limit Exceeded', 'high', f"Blocked login attempt from IP: {ip_addr}")
            flash('Terlalu banyak percobaan login gagal. Silakan coba lagi dalam 10 menit.', 'error')
            return render_template('auth/login.html', hide_chrome=True)

        # 2. Check WAF (Suspicious Input)
        is_suspicious, threat_type = detect_suspicious_input(email)
        if is_suspicious:
            log_security(threat_type, 'high', f"Blocked suspicious input: {email}")
            flash('Input terdeteksi berbahaya dan diblokir!', 'error')
            return render_template('auth/login.html', hide_chrome=True)
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']; session['username'] = user['username']
            session['role'] = user['role']; session['wallet'] = user['wallet_address']
            session['profile_pic'] = user['profile_pic'] if user['profile_pic'] else 'default_user.png'
            log_security('Login Success', 'low', f"User {user['username']} logged in successfully.", user['id'])
            return redirect(url_for('dashboard'))
        else: 
            record_failed_attempt(ip_addr)
            flash('Login gagal! Cek email/password.', 'error')
            log_security('Login Failed', 'medium', f"Failed login attempt for email: {email}")
    return render_template('auth/login.html', hide_chrome=True)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user:
            # Generate Token (valid 15 minutes)
            s = URLSafeTimedSerializer(app.secret_key)
            token = s.dumps(email, salt='email-reset')
            send_reset_password_email(email, token)
        
        # Always flash success to prevent email enumeration
        flash('Jika email terdaftar, link reset password telah dikirim.', 'info')
        return redirect(url_for('login'))
        
    return render_template('auth/forgot_password.html', hide_chrome=True)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        s = URLSafeTimedSerializer(app.secret_key)
        email = s.loads(token, salt='email-reset', max_age=900) # 15 minutes
    except:
        flash('Link reset password tidak valid atau sudah kadaluwarsa.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']
        
        # Update Password
        conn = get_db_connection()
        conn.execute('UPDATE users SET password = ? WHERE email = ?', (password, email))
        conn.commit(); conn.close()
        
        log_security('Password Reset', 'medium', f"User {email} reset their password.")
        flash('Password berhasil diubah! Silakan login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('auth/reset_password.html', hide_chrome=True, token=token)

@app.route('/register', methods=['GET', 'POST'])
def register():
    ganache_accounts = []
    if web3 and web3.is_connected():
        try: 
            all_accounts = web3.eth.accounts
            # Filter Used Wallets
            conn = get_db_connection()
            used_wallets_rows = conn.execute("SELECT wallet_address FROM users").fetchall()
            conn.close()
            
            used_wallets = {row['wallet_address'] for row in used_wallets_rows}
            ganache_accounts = [acc for acc in all_accounts if acc not in used_wallets]
        except: pass
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        wallet = request.form['wallet_address']
        pk = request.form['private_key']

        # 1. STRICT EMAIL VALIDATION (Gmail Only)
        if not re.match(r"^[a-zA-Z0-9_.+-]+@gmail\.com$", email):
            # Log threat even if it's just a format mismatch, as it could be an attempt to bypass
            log_security("Invalid Email Format", 'medium', f"Attempted registration with non-Gmail email: {email}")
            flash("Registrasi Ditolak: Hanya email Google (@gmail.com) yang diperbolehkan!", "error")
            return render_template('auth/register.html', accounts=ganache_accounts, hide_chrome=True)

        # 2. STRICT USERNAME VALIDATION (Instagram-like: lowercase, alphanumeric, dot, underscore)
        if not re.match(r"^[a-z0-9_.]+$", username):
            log_security("Invalid Username Format", 'medium', f"Invalid username format: {username}")
            flash("Username tidak valid! Hanya huruf kecil (a-z), angka, titik (.), dan underscore (_) yang diperbolehkan.", "error")
            return render_template('auth/register.html', accounts=ganache_accounts, hide_chrome=True)
        
        # WAF Check
        for field, val in [('Username', username), ('Email', email), ('Wallet', wallet)]:
            is_suspicious, threat_type = detect_suspicious_input(val)
            if is_suspicious:
                log_security(threat_type, 'high', f"Blocked suspicious register input in {field}: {val}")
                flash(f'Input {field} terdeteksi berbahaya!', 'error')
                return render_template('auth/register.html', accounts=ganache_accounts, hide_chrome=True)

        if web3 and not Web3.is_address(wallet):
            flash('Alamat Wallet Ethereum tidak valid!', 'error')
            return render_template('auth/register.html', accounts=ganache_accounts, hide_chrome=True)

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, email, password, role, wallet_address, private_key, profile_pic) VALUES (?, ?, ?, ?, ?, ?, ?)',
                         (username, email, password, role, wallet, pk, 'default_user.png'))
            conn.commit()
            
            # Ambil ID Pengguna Baru untuk Log
            new_user_id = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()['id']
            log_security('Registration', 'low', f"New user registered: {username} ({role})", new_user_id)
            
            # KIRIM EMAIL NOTIFIKASI
            # (Best practice: Gunakan Threading/Celery agar tidak blocking, tapi untuk demo ini sync tidak masalah jika koneksi cepat)
            send_welcome_email(email, username)
            
            flash('Registrasi berhasil! Setup Wallet selesai.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email atau Username sudah terdaftar.', 'error')
        except Exception as e:
            flash(f'Gagal Register: {e}', 'error')
        finally: conn.close()
    return render_template('auth/register.html', accounts=ganache_accounts, hide_chrome=True)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        new_username = request.form.get('username'); bio = request.form.get('bio')
        file = request.files.get('profile_pic')
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        msg = []
        if new_username and new_username != user['username']:
            conn.execute("UPDATE users SET username = ?, last_username_change = ? WHERE id = ?", (new_username, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session['user_id']))
            session['username'] = new_username; msg.append("Username berhasil diubah.")
        
        conn.execute("UPDATE users SET bio = ? WHERE id = ?", (bio, session['user_id']))
        if file and file.filename != '':
            if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
            filename = f"user_{session['user_id']}_{int(time.time())}.jpg"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute("UPDATE users SET profile_pic = ? WHERE id = ?", (filename, session['user_id']))
            session['profile_pic'] = filename; msg.append("Foto profil diperbarui.")
        conn.commit()
        if msg: flash("Profil berhasil diperbarui!", "success")
        return redirect(url_for('profile'))
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    balance = "0"
    try: 
        if web3: balance = "{:.4f}".format(web3.from_wei(web3.eth.get_balance(user['wallet_address']), 'ether'))
    except: pass
    conn.close()
    return render_template('profile.html', user=user, balance=balance, days_wait=0, hide_chrome=True)

# --- 6. ROUTES CAMPAIGN ---
@app.route('/dashboard')
def dashboard():
    if session.get('role') == 'admin': return redirect(url_for('admin_dashboard'))
    
    campaigns = []
    if contract:
        try:
            count = contract.functions.getCampaignCount().call()
            conn = get_db_connection()
            details_rows = conn.execute("SELECT * FROM campaign_details").fetchall()
            conn.close()
            details_map = {d['blockchain_id']: d for d in details_rows}
            
            current_time = time.time()
            
            for i in range(count):
                c = contract.functions.getCampaign(i).call()
                # c structure: [id, creator, title, desc, target, collected, image, deadline, status, withdrawn]
                
                status_code = c[8]
                creator_address = c[1]
                deadline_ts = c[7]
                
                # Filter Logic
                is_owner = (creator_address == session.get('wallet'))
                should_show = False
                if status_code == 1: should_show = True
                elif is_owner: should_show = True
                if status_code == 3: should_show = False
                
                if should_show:
                    status_label = 'Pending' if status_code == 0 else 'Active' if status_code == 1 else 'Rejected'
                    detail = details_map.get(c[0])
                    
                    # --- LOGIKA HITUNG WAKTU TERSISA (UPDATED) ---
                    remaining_text = "Selesai"
                    is_expired = False
                    
                    time_diff = deadline_ts - current_time
                    if time_diff > 0:
                        days = int(time_diff // 86400)
                        hours = int((time_diff % 86400) // 3600)
                        if days > 0:
                            remaining_text = f"{days} Hari Lagi"
                        else:
                            remaining_text = f"{hours} Jam Lagi"
                    else:
                        is_expired = True
                        remaining_text = "Waktu Habis"
                    
                    deadline_date = datetime.fromtimestamp(deadline_ts).strftime('%d %b %Y')
                    
                    campaigns.append({
                        'id': c[0], 'title': c[2], 'desc': c[3],
                        'target': web3.from_wei(c[4], 'ether'),
                        'collected': web3.from_wei(c[5], 'ether'),
                        'image': c[6], 'status_code': status_code,
                        'status_label': status_label, 'is_owner': is_owner,
                        'tagline': detail['tagline'] if detail else c[3][:50] + "...",
                        'category': detail['category'] if detail else "Umum",
                        
                        # Data Waktu Baru
                        'deadline_date': deadline_date,
                        'remaining_text': remaining_text,
                        'is_expired': is_expired
                    })
        except Exception as e: print(f"Dashboard Error: {e}")
    return render_template('campaigns.html', campaigns=campaigns)

@app.route('/create_campaign', methods=['GET', 'POST'])
def create_campaign():
    if 'user_id' not in session: flash("Silakan login.", "error"); return redirect(url_for('login'))
    if session.get('role') != 'kreator': flash("Hanya Kreator!", "error"); return redirect(url_for('dashboard'))
    
    prefill_title = request.args.get('title', '')
    
    if request.method == 'POST':
        title = request.form['title']; desc = request.form['description']
        target = float(request.form['target'])
        
        # Ambil Durasi (Default 30 hari jika tidak diisi)
        try: duration_days = int(request.form['duration'])
        except: duration_days = 30
        
        category = request.form.get('category', 'Umum')
        tagline = request.form.get('tagline', '')
        usage_plan = request.form.get('usage_plan', '')
        social_link = request.form.get('social_link', '')
        file = request.files['image']
        
        if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
        filename = f"{int(time.time())}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        conn = get_db_connection()
        user_data = conn.execute("SELECT wallet_address, private_key FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        
        try:
            target_wei = web3.to_wei(target, 'ether')
            # Konversi hari ke menit (karena smart contract pakai menit) -> 1 hari = 1440 menit
            duration_minutes = duration_days * 1440
            
            # UPDATE: Use 'pending' nonce for currency
            nonce = web3.eth.get_transaction_count(user_data['wallet_address'], 'pending')
            
            # Panggil fungsi Smart Contract
            txn = contract.functions.createCampaign(title, desc, target_wei, filename, duration_minutes).build_transaction({
                'chainId': web3.eth.chain_id, 'gas': 2000000, 'gasPrice': web3.eth.gas_price, 'nonce': nonce
            })
            signed_txn = web3.eth.account.sign_transaction(txn, private_key=user_data['private_key'])
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            # NOTE: Create Campaign tetap Blocking agar kita bisa dapat ID campaign yang valid
            web3.eth.wait_for_transaction_receipt(tx_hash)
            
            new_count = contract.functions.getCampaignCount().call()
            conn.execute('INSERT INTO campaign_details (blockchain_id, category, usage_plan, social_link, tagline) VALUES (?, ?, ?, ?, ?)',
                         (new_count - 1, category, usage_plan, social_link, tagline))
            
            # --- EMAIL NOTIF: PENDING (KE KREATOR) ---
            try:
                creator_email = conn.execute("SELECT email, username FROM users WHERE id = ?", (session['user_id'],)).fetchone()
                send_campaign_notification(creator_email['email'], creator_email['username'], title, 'pending')
            except: pass

            conn.commit(); conn.close()
            flash(f"Campaign dibuat! Nonce: {nonce}", "success"); return redirect(url_for('dashboard'))
        except Exception as e: conn.close(); flash(f"Error Blockchain: {str(e)}", "error")
    return render_template('create_campaign.html', prefill_title=prefill_title, hide_chrome=True)

@app.route('/campaign/<int:id>')
def campaign_detail(id):
    try:
        c = contract.functions.getCampaign(id).call()
        conn = get_db_connection()
        detail = conn.execute("SELECT * FROM campaign_details WHERE blockchain_id = ?", (id,)).fetchone()
        updates = conn.execute("SELECT * FROM campaign_updates WHERE blockchain_id = ? ORDER BY id DESC", (id,)).fetchall()
        
        # UPDATE: Ambil donasi dari DB agar bisa menampilkan nonce
        donations = conn.execute("SELECT * FROM donations WHERE blockchain_id = ? ORDER BY id DESC", (id,)).fetchall()
        
        conn.close()
        target = web3.from_wei(c[4], 'ether'); collected = web3.from_wei(c[5], 'ether')
        percent = (float(collected) / float(target) * 100) if float(target) > 0 else 0
        
        campaign = {
            'id': c[0], 'creator': c[1], 'creator_name': get_username_by_wallet(c[1]),
            'title': c[2], 'desc': c[3], 'target': target, 'collected': collected,
            'image': c[6], 'deadline': time.ctime(c[7]), 'status_code': c[8],
            'percent': "{:.1f}".format(percent), 'fundsWithdrawn': c[9],
            'category': detail['category'] if detail else 'Umum',
            'tagline': detail['tagline'] if detail else '',
            'usage_plan': detail['usage_plan'] if detail else 'Tidak ada rincian.',
            'social_link': detail['social_link'] if detail else '#',
            'updates': updates, 'donations': donations
        }
        return render_template('campaign_detail.html', campaign=campaign)
    except Exception as e: flash(f"Gagal memuat kampanye: {e}", "error"); return redirect(url_for('dashboard'))

@app.route('/donate/<int:id>', methods=['POST'])
def donate(id):
    if session.get('role') != 'donatur': return redirect(url_for('campaign_detail', id=id))
    amount = request.form.get('amount'); message = request.form.get('message')
    try:
        amount_eth = float(amount)
        amount_wei = web3.to_wei(amount_eth, 'ether')
        
        if amount_eth <= 0:
            flash("Jumlah donasi harus lebih dari 0!", "error")
            return redirect(url_for('campaign_detail', id=id))

        conn = get_db_connection()
        user_data = conn.execute("SELECT wallet_address, private_key, username FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        
        # 1. Estimasi Gas Fee (Dynamic)
        try:
            gas_limit = contract.functions.donateToCampaign(id).estimate_gas({'from': user_data['wallet_address'], 'value': amount_wei})
            # Tambahkan buffer sedikit untuk keamanan
            gas_limit = int(gas_limit * 1.1) 
        except Exception as e:
            # Fallback jika estimasi gagal (misal saldo 0 di ganache sering fail estimasi)
            print(f"Gas Estimation Failed: {e}")
            gas_limit = 200000 # Fallback yang lebih masuk akal daripada 2 juta
            
        gas_price = web3.eth.gas_price
        total_cost_wei = amount_wei + (gas_limit * gas_price)
        
        # 2. Pengecekan Saldo
        sender_balance_wei = web3.eth.get_balance(user_data['wallet_address'])
        
        if sender_balance_wei < total_cost_wei:
            shortage = web3.from_wei(total_cost_wei - sender_balance_wei, 'ether')
            flash(f"Saldo tidak cukup untuk Donasi + Gas Fee. Estimasi Fee: {web3.from_wei(gas_limit*gas_price, 'gwei')} Gwei. Kekurangan: {shortage:.5f} ETH", "error")
            log_security('Low Balance', 'medium', f"User {user_data['username']} low balance. Req: {web3.from_wei(total_cost_wei,'ether')} ETH", session['user_id'])
            return redirect(url_for('campaign_detail', id=id))

        # 3. Eksekusi
        nonce = web3.eth.get_transaction_count(user_data['wallet_address'], 'pending')
        
        txn = contract.functions.donateToCampaign(id).build_transaction({
            'chainId': web3.eth.chain_id, 'gas': gas_limit, 'gasPrice': gas_price, 'nonce': nonce, 'value': amount_wei 
        })
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=user_data['private_key'])
        
        # Kirim Tx (ASYNC - No Wait)
        tx_hash_bytes = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        # web3.eth.wait_for_transaction_receipt(tx_hash_bytes) <-- REMOVED BLOCKING CALL
        tx_hash_str = tx_hash_bytes.hex()
        
        # 2. Simpan ke Database (UPDATE: simpan nonce dan hash)
        conn.execute('''INSERT INTO donations (blockchain_id, donor_name, amount, message, timestamp, tx_hash, nonce) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (id, user_data['username'], amount, message, datetime.now().strftime("%d %b %Y, %H:%M"), tx_hash_str, nonce))
        
        conn.commit(); conn.close()
        log_security('Donation Initiated', 'medium', f"Donated {amount} ETH to Campaign #{id}. Tx: {tx_hash_str[:10]}...")
        flash(f"Terima kasih! Donasi berhasil. Nonce: #{nonce}", "success")
    except Exception as e: 
        log_security('Donation Failed', 'high', f"Failed to donate: {str(e)}")
        flash(f"Gagal Donasi: {e}", "error")
    return redirect(url_for('campaign_detail', id=id))

@app.route('/post_update/<int:id>', methods=['POST'])
def post_update(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    title = request.form['update_title']; content = request.form['update_content']
    file = request.files['update_image']; image_filename = ""
    if file:
        filename = f"update_{int(time.time())}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image_filename = filename
    conn = get_db_connection()
    conn.execute('INSERT INTO campaign_updates (blockchain_id, title, content, image, created_at) VALUES (?, ?, ?, ?, ?)',
                 (id, title, content, image_filename, time.ctime()))
    
    # --- EMAIL UPDATE TO DONORS ---
    try:
        # 1. Fetch Campaign Title
        campaign = contract.functions.getCampaign(id).call()
        campaign_title = campaign[2]
        
        # 2. Get Donors
        donors = get_donor_emails(id)
        
        # 3. Send Emails
        if donors:
            send_update_email(donors, campaign_title, title, content, image_filename)
    except Exception as e:
        print(f"Error sending update emails: {e}")
        
    conn.commit(); conn.close()
    flash("Kabar terbaru berhasil diposting!", "success"); return redirect(url_for('campaign_detail', id=id))

@app.route('/withdraw/<int:id>')
def withdraw_funds(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection(); user_data = conn.execute("SELECT wallet_address, private_key FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    try:
        # 1. Ambil Nonce 'pending'
        nonce = web3.eth.get_transaction_count(user_data['wallet_address'], 'pending')
        
        txn = contract.functions.withdrawFunds(id).build_transaction({
            'chainId': web3.eth.chain_id, 'gas': 2000000, 'gasPrice': web3.eth.gas_price, 'nonce': nonce
        })
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=user_data['private_key'])
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        # web3.eth.wait_for_transaction_receipt(tx_hash) <-- ASYNC
        log_security('Withdrawal Funds', 'medium', f"Withdrawal initiated for Campaign #{id}. Tx: {tx_hash.hex()[:10]}...")
        flash(f"Penarikan sedang diproses blockchain (Tx: {tx_hash.hex()[:10]}...)", "success")
        
        # --- EMAIL WITHDRAWAL NOTIF ---
        try:
            # 1. Title
            campaign = contract.functions.getCampaign(id).call()
            title = campaign[2]
            # 2. Donors
            donors = get_donor_emails(id)
            # 3. Send
            if donors:
                send_withdrawal_email(donors, title)
        except Exception as e: print(f"Error withdrawal email: {e}")
        
    except Exception as e: 
        log_security('Withdrawal Failed', 'high', f"Failed to withdraw Campaign #{id}: {str(e)}")
        flash(f"Gagal Tarik Dana: {e}", "error")
    return redirect(url_for('campaign_detail', id=id))

@app.before_request
def track_visitor():
    if not session.get('visited'):
        session['visited'] = True
        user_agent = request.user_agent.string
        device_type = "Mobile" if "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent else "Desktop"
        log_security('Site Visit', 'info', f"New visitor: {device_type} ({request.user_agent.platform})")

# --- 8. ADMIN PANEL ---
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    if session.get('role') != 'admin': return redirect(url_for('index'))
    
    conn = get_db_connection()
    stats = {'total_campaigns': 0, 'pending': 0, 'active': 0, 'rejected': 0, 'deleted': 0}
    campaigns_data = []
    users_rows = conn.execute("SELECT * FROM users").fetchall()
    
    if contract:
        try:
            count = contract.functions.getCampaignCount().call()
            stats['total_campaigns'] = count
            db_details = conn.execute("SELECT * FROM campaign_details").fetchall()
            
            for i in range(count):
                c = contract.functions.getCampaign(i).call()
                status_code = c[8]; creator_addr = c[1]
                if status_code == 0: stats['pending'] += 1
                elif status_code == 1: stats['active'] += 1
                elif status_code == 2: stats['rejected'] += 1
                elif status_code == 3: stats['deleted'] += 1
                
                campaigns_data.append({
                    'id': c[0], 'title': c[2],
                    'description': c[3],
                    'target': web3.from_wei(c[4], 'ether'),
                    'collected': web3.from_wei(c[5], 'ether'),
                    'image': c[6],
                    'deadline': datetime.fromtimestamp(c[7]).strftime('%d %b %Y'),
                    'creator_name': get_username_by_wallet(creator_addr),
                    'creator_addr': creator_addr,
                    'status_code': status_code,
                    'status': 'Pending' if status_code==0 else 'Active' if status_code==1 else 'Rejected'
                })
        except: pass

    transactions_log = get_all_transactions()
    ganache_accounts = []; network_status = "Offline"
    
    if web3 and web3.is_connected():
        network_status = "Connected"
        try:
            for i, acc in enumerate(web3.eth.accounts):
                bal = web3.from_wei(web3.eth.get_balance(acc), 'ether')
                ganache_accounts.append({'index': i, 'address': acc, 'balance': "{:.4f}".format(bal)})
        except: pass

    # --- REAL SECURITY LOGS (FETCH FROM DB) ---
    security_logs_rows = conn.execute("SELECT * FROM security_logs ORDER BY id DESC LIMIT 20").fetchall()
    
    # Calculate Real Traffic Stats
    today_visit_count = conn.execute("SELECT COUNT(*) FROM security_logs WHERE action='Site Visit' AND timestamp LIKE ?", (datetime.now().strftime("%d %b %Y") + '%',)).fetchone()[0]
    mobile_count = conn.execute("SELECT COUNT(*) FROM security_logs WHERE action='Site Visit' AND description LIKE '%Mobile%'").fetchone()[0]
    all_visits_count = conn.execute("SELECT COUNT(*) FROM security_logs WHERE action='Site Visit'").fetchone()[0]
    
    if all_visits_count > 0:
        mobile_percent = int((mobile_count / all_visits_count) * 100)
    else:
        mobile_percent = 0
    desktop_percent = 100 - mobile_percent
    
    visitor_stats = { 
        'total_visits': today_visit_count, 
        'unique_visitors': all_visits_count, 
        'mobile_percent': mobile_percent, 
        'desktop_percent': desktop_percent 
    }

    # Mapper untuk format consistent di Frontend
    security_logs = []
    for log in security_logs_rows:
        # log structure: id, timestamp, ip_address, action, status, description, user_id
        security_logs.append({
            'time': log['timestamp'],
            'ip': log['ip_address'],
            'action': log['action'],
            'status': log['status'], # low, medium, high, info
            'desc': log['description']
        })

    conn.close()
    return render_template('admin_dashboard.html', stats=stats, total_users=len(users_rows),
                           campaigns=campaigns_data, users=users_rows, transactions=transactions_log,
                           ganache_accounts=ganache_accounts, network_status=network_status,
                           security_logs=security_logs, visitor_stats=visitor_stats)

@app.route('/admin/approve/<int:id>')
def approve_campaign(id):
    if session.get('role') != 'admin': return redirect(url_for('index'))
    try:
        # ASYNC
        nonce = web3.eth.get_transaction_count(web3.eth.accounts[0], 'pending')
        tx = contract.functions.approveCampaign(id).transact({'from': web3.eth.accounts[0], 'nonce': nonce})
        # web3.eth.wait_for_transaction_receipt(tx); 
        log_security('Admin Approve', 'high', f"Admin approved Campaign #{id}")

        # --- EMAIL NOTIF: APPROVED ---
        try:
            # Fetch Blockchain Data Sync for Email Info
            c_data = contract.functions.getCampaign(id).call()
            # c_data[1] = creator address, c_data[2] = title
            conn = get_db_connection()
            user = conn.execute("SELECT email, username FROM users WHERE wallet_address = ?", (c_data[1],)).fetchone()
            conn.close()
            if user:
                send_campaign_notification(user['email'], user['username'], c_data[2], 'approved')
        except Exception as e: print(f"Email Fail: {e}")

        flash(f"Campaign #{id} Approve broadcasted..", "success")
    except Exception as e: flash(f"Gagal approve: {e}", "error")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_campaign/<int:id>')
def delete_campaign(id):
    if session.get('role') != 'admin': return redirect(url_for('index'))
    try:
        # ASYNC
        nonce = web3.eth.get_transaction_count(web3.eth.accounts[0], 'pending')
        tx = contract.functions.deleteCampaign(id).transact({'from': web3.eth.accounts[0], 'nonce': nonce})
        # web3.eth.wait_for_transaction_receipt(tx); 
        log_security('Admin Delete', 'high', f"Admin soft-deleted Campaign #{id}")

        # --- EMAIL NOTIF: REJECTED ---
        try:
            c_data = contract.functions.getCampaign(id).call()
            conn = get_db_connection()
            user = conn.execute("SELECT email, username FROM users WHERE wallet_address = ?", (c_data[1],)).fetchone()
            conn.close()
            if user:
                send_campaign_notification(user['email'], user['username'], c_data[2], 'rejected')
        except: pass

        flash(f"Campaign #{id} Delete broadcasted.", "success")
    except Exception as e: flash(f"Gagal hapus: {e}", "error")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if session.get('role') != 'admin': return redirect(url_for('index'))
    try:
        conn = get_db_connection(); conn.execute('DELETE FROM users WHERE id = ?', (user_id,)); conn.commit(); conn.close()
        flash(f"User ID {user_id} dihapus.", "success")
    except: flash("Gagal hapus user", "error")
    return redirect(url_for('admin_dashboard'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', hide_chrome=True), 404

@app.route('/explorer')
def explorer():
    return render_template('explorer.html')

@app.route('/api/explorer-data')
def explorer_data_api():
    transactions = []
    all_blocks = []
    network_stats = {'gasPrice': 0, 'blockTime': 0, 'difficulty': 0}
    # Data Tambahan: Smart Contract Info
    contract_info = {'address': 'N/A', 'balance': '0', 'campaign_count': 0}
    
    if contract and web3 and web3.is_connected():
        try:
            # 1. Ambil Info Kontrak (VAULT)
            contract_info['address'] = contract.address
            # Saldo ETH di dalam kontrak
            raw_bal = web3.eth.get_balance(contract.address)
            contract_info['balance'] = "{:.4f}".format(web3.from_wei(raw_bal, 'ether'))
            contract_info['campaign_count'] = contract.functions.getCampaignCount().call()

            # 2. Transaksi (Event Logs)
            events_donate = contract.events.DonationReceived().get_logs(fromBlock=0)
            for e in events_donate:
                tx_hash = e['transactionHash'].hex()
                nonce = "N/A"
                try:
                    tx_detail = web3.eth.get_transaction(tx_hash)
                    nonce = tx_detail['nonce']
                except: pass
                transactions.append({'hash': tx_hash, 'from': e['args']['donor'], 'amount': web3.from_wei(e['args']['amount'], 'ether'), 'nonce': nonce, 'time': datetime.fromtimestamp(e['args']['timestamp']).strftime('%H:%M:%S'), 'timestamp_raw': e['args']['timestamp'], 'type': 'Donation'})
            
            events_create = contract.events.CampaignCreated().get_logs(fromBlock=0)
            for e in events_create:
                tx_hash = e['transactionHash'].hex()
                nonce = "N/A"
                try:
                    tx_detail = web3.eth.get_transaction(tx_hash)
                    nonce = tx_detail['nonce']
                except: pass
                transactions.append({'hash': tx_hash, 'from': e['args']['creator'], 'amount': '0.0', 'nonce': nonce, 'time': datetime.fromtimestamp(e['args']['timestamp']).strftime('%H:%M:%S'), 'timestamp_raw': e['args']['timestamp'], 'type': 'New Campaign'})
            
            transactions.sort(key=lambda x: x['timestamp_raw'], reverse=True)

            # 3. Blocks
            current_block_num = web3.eth.block_number
            network_stats['gasPrice'] = web3.from_wei(web3.eth.gas_price, 'gwei')
            start_block = max(0, current_block_num - 50)
            for i in range(start_block, current_block_num + 1):
                blk = web3.eth.get_block(i)
                all_blocks.append({'number': blk.number, 'hash': blk.hash.hex(), 'tx_count': len(blk.transactions), 'timestamp': datetime.fromtimestamp(blk.timestamp).strftime('%H:%M:%S'), 'gasUsed': blk.gasUsed})
        except Exception as e:
            print(f"API Error: {e}")
    
    return {
        'transactions': transactions, 
        'blocks': all_blocks, 
        'stats': network_stats,
        'contract': contract_info  # Data baru dikirim ke frontend
    }

@app.route('/api/latest-activity')
def get_latest_activity():
    try:
        # Header agar tidak di-cache browser (Penting!)
        response_headers = {
            'Cache-Control': 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0',
            'Pragma': 'no-cache',
            'Expires': '0'
        }

        if not contract: 
            return ({'status': 'error', 'msg': 'Contract not connected'}, 200, response_headers)
        
        # Ambil block terbaru
        current_block = web3.eth.block_number
        # Cari log dari 1000 block terakhir (cukup aman & cepat)
        start_search = max(0, current_block - 1000)
        
        events = contract.events.DonationReceived().get_logs(fromBlock=start_search)
        
        if not events:
            return ({'status': 'empty'}, 200, response_headers)
            
        # Ambil event PALING BARU (index terakhir)
        latest_event = events[-1]
        args = latest_event['args']
        
        # Cek Database untuk ambil Nama User
        conn = get_db_connection()
        user = conn.execute("SELECT username, role FROM users WHERE wallet_address = ?", (args['donor'],)).fetchone()
        conn.close()
        
        role = user['role'] if user else 'Guest'
        username = user['username'] if user else 'Anonymous'
        
        data = {
            'status': 'success',
            'tx_hash': latest_event['transactionHash'].hex(),
            'from_wallet': args['donor'],
            'username': username,
            'role': role.capitalize(),
            'amount': "{:.4f}".format(web3.from_wei(args['amount'], 'ether')),
            'campaign_id': args['campaignId'],
            'timestamp': args['timestamp']
        }
        return (data, 200, response_headers)

    except Exception as e:
        print(f"API Error: {e}")
        return ({'status': 'error', 'msg': str(e)}, 200, response_headers)


if __name__ == '__main__':
    # LISTEN ON ALL INTERFACES for Local Network Access
    app.run(debug=True, host='0.0.0.0', port=5000)