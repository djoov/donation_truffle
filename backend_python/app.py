from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from contract_data import web3, contract
from datetime import datetime
import time
import os

app = Flask(__name__)

# --- Konfigurasi App ---
app.config['SECRET_KEY'] = 'rahasia_super_aman_123' # Ganti dengan key acak yang kuat
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Inisialisasi Ekstensi ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Redirect ke sini jika user belum login
login_manager.login_message_category = 'info'

# --- Model Database (Tabel User) ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='donor') # 'admin', 'creator', 'donor'
    wallet_address = db.Column(db.String(42), nullable=True) # Alamat wallet opsional

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.role}')"

# Fungsi helper untuk Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================
# UTILITY & HELPER
# ============================
def get_status_label(status_int):
    statuses = {0: "Pending", 1: "Active", 2: "Ended", 3: "Rejected"}
    return statuses.get(status_int, "Unknown")


# ============================
# AUTH ROUTES (Login, Register, Logout)
# ============================

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role') # creator / donor
        wallet = request.form.get('wallet_address')

        # Cek apakah user sudah ada
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email sudah terdaftar. Silakan login.', 'danger')
            return redirect(url_for('register'))

        # Hash password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Buat user baru (role admin harus di-set manual di DB untuk keamanan, default via form hanya creator/donor)
        if role not in ['creator', 'donor']:
            role = 'donor'
            
        user = User(username=username, email=email, password=hashed_password, role=role, wallet_address=wallet)
        db.session.add(user)
        db.session.commit()
        
        flash(f'Akun {username} berhasil dibuat! Silakan login.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Login berhasil!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login gagal. Cek email dan password.', 'danger')
            
    return render_template('auth/login.html')


@app.route("/logout")
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('index'))


# ============================
# MAIN ROUTES
# ============================

@app.route('/')
def index():
    try:
        count = contract.functions.getCampaignCount().call()
        campaigns = []
        for i in range(count - 1, -1, -1):
            try:
                camp = contract.functions.getCampaign(i).call()
                amount_eth = web3.from_wei(camp[3], 'ether')
                is_active = (camp[2] > time.time()) and (camp[4] == 1)
                
                campaign_data = {
                    'id': i,
                    'creator': camp[0],
                    'title': camp[1],
                    'deadline': datetime.fromtimestamp(camp[2]).strftime('%d %b %Y'),
                    'amount_raised': amount_eth,
                    'status_code': camp[4],
                    'status_label': get_status_label(camp[4]),
                    'is_active': is_active
                }
                campaigns.append(campaign_data)
            except Exception:
                continue
        return render_template('index.html', campaigns=campaigns)
    except Exception as e:
        return f"Error: {str(e)}"


@app.route("/ui/create", methods=["GET", "POST"])
@login_required # Hanya user login yang bisa akses
def ui_create():
    # Validasi Role: Hanya Creator atau Admin yang boleh buat
    if current_user.role not in ['creator', 'admin']:
        flash('Anda harus mendaftar sebagai Kreator untuk membuat kampanye.', 'warning')
        return redirect(url_for('index'))

    if request.method == "POST":
        try:
            data = request.form
            # Gunakan wallet dari database jika user tidak input manual (opsional)
            from_addr = data.get("from") 
            
            tx = contract.functions.createCampaign(
                data["title"],
                int(data["duration"])
            ).build_transaction({
                "from": from_addr,
                "nonce": web3.eth.get_transaction_count(from_addr),
                "gas": 3000000,
                "gasPrice": web3.eth.gas_price
            })
            
            signed_tx = web3.eth.account.sign_transaction(tx, private_key=data["private_key"])
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            flash('Kampanye berhasil diajukan! Menunggu persetujuan Admin.', 'success')
            return redirect(url_for('index'))
        
        except Exception as e:
            flash(f'Gagal membuat kampanye: {str(e)}', 'danger')

    return render_template("create_campaign.html")


@app.route("/ui/donate/<int:id>", methods=["GET", "POST"])
@login_required # Hanya user login yang bisa donasi
def donate_page(id):
    try:
        c = contract.functions.getCampaign(id).call()
        data = {"id": id, "title": c[1], "totalDonations": web3.from_wei(c[3], 'ether')}
        
        if request.method == "POST":
            form = request.form
            amount_wei = web3.to_wei(form["amount"], "ether")
            
            tx = contract.functions.donateToCampaign(id).build_transaction({
                "from": form["from"],
                "value": amount_wei,
                "nonce": web3.eth.get_transaction_count(form["from"]),
                "gas": 3000000,
                "gasPrice": web3.eth.gas_price
            })
            signed_tx = web3.eth.account.sign_transaction(tx, private_key=form["private_key"])
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            flash('Donasi berhasil dikirim! Terima kasih.', 'success')
            return redirect(url_for('campaign_detail', id=id))

        return render_template("donate_page.html", c=data)
    except Exception as e:
        return f"Error: {str(e)}"


@app.route("/ui/admin")
@login_required
def admin_dashboard():
    # Validasi Role: Hanya Admin
    if current_user.role != 'admin':
        flash('Akses ditolak. Halaman ini khusus Admin.', 'danger')
        return redirect(url_for('index'))

    try:
        total = contract.functions.getCampaignCount().call()
        data = []
        for i in range(total):
            c = contract.functions.getCampaign(i).call()
            data.append({
                "id": i,
                "creator": c[0],
                "title": c[1],
                "deadline": datetime.fromtimestamp(c[2]).strftime('%d/%m/%Y'),
                "totalDonations": web3.from_wei(c[3], 'ether'),
                "status_label": get_status_label(c[4]),
                "status_code": c[4]
            })
        return render_template("admin_dashboard.html", campaigns=data)
    except Exception as e:
         return f"Error: {str(e)}"

# Route admin action dan campaign detail tetap sama, hanya perlu disesuaikan sedikit jika mau proteksi lebih.
@app.route("/ui/campaign/<int:id>")
def campaign_detail(id):
    try:
        c = contract.functions.getCampaign(id).call()
        data = {
            "id": id, "creator": c[0], "title": c[1],
            "deadline": datetime.fromtimestamp(c[2]).strftime('%d %b %Y %H:%M'),
            "totalDonations": web3.from_wei(c[3], 'ether'),
            "status_code": c[4], "status_label": get_status_label(c[4]),
            "is_active": (c[2] > time.time()) and (c[4] == 1)
        }
        return render_template("campaign_detail.html", c=data)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/ui/admin/action/<string:action>/<int:id>", methods=["POST"])
@login_required
def admin_action(action, id):
    if current_user.role != 'admin':
        return "Unauthorized", 403
    # ... (Logika transaksi sama seperti app.py sebelumnya) ...
    sender = request.form.get("from")
    private_key = request.form.get("private_key")

    try:
        if action == "approve": func = contract.functions.approveCampaign(id)
        elif action == "reject": func = contract.functions.rejectCampaign(id)
        elif action == "disable": func = contract.functions.disableCampaign(id)
        else: return "Invalid action"

        tx = func.build_transaction({
            "from": sender, "nonce": web3.eth.get_transaction_count(sender),
            "gas": 3000000, "gasPrice": web3.eth.gas_price
        })
        signed_tx = web3.eth.account.sign_transaction(tx, private_key=private_key)
        web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        flash(f'Kampanye #{id} berhasil di-{action}.', 'success')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Gagal: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

# --- Inisialisasi Database saat pertama kali run ---
with app.app_context():
    db.create_all()
    # Opsional: Buat 1 user admin default jika belum ada
    if not User.query.filter_by(username='admin').first():
        hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin = User(username='admin', email='admin@platform.com', password=hashed_pw, role='admin', wallet_address='0xYourAdminWallet')
        db.session.add(admin)
        db.session.commit()
        print("User admin default dibuat: email=admin@platform.com, pass=admin123")

if __name__ == "__main__":
    app.run(debug=True, port=5000)