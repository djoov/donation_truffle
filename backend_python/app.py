from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from contract_data import web3, contract
from datetime import datetime
import time
import os

app = Flask(__name__)

# --- Konfigurasi App ---
app.config['SECRET_KEY'] = 'rahasia_super_aman_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Konfigurasi Upload
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Inisialisasi Ekstensi ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- Utility ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_status_label(status_int):
    statuses = {0: "Pending", 1: "Active", 2: "Ended", 3: "Rejected", 4: "Disabled"}
    return statuses.get(status_int, "Unknown")

# --- Model Database ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='donor') 
    wallet_address = db.Column(db.String(42), nullable=True)
    # [BARU] Simpan Private Key di DB (Hanya untuk DEV/DEMO! Jangan di Production)
    private_key = db.Column(db.String(100), nullable=True) 

class CampaignData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================
# ROUTES
# ============================

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Ambil daftar akun dari Ganache untuk Dropdown
    ganache_accounts = web3.eth.accounts

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'donor')
        wallet = request.form.get('wallet_address') # Dipilih dari dropdown
        p_key = request.form.get('private_key')     # Diinput sekali

        # Validasi: Cek apakah Wallet Address cocok dengan Private Key
        try:
            check_acc = web3.eth.account.from_key(p_key)
            if check_acc.address.lower() != wallet.lower():
                flash(f'Private Key tidak cocok dengan Address {wallet}!', 'danger')
                return render_template('auth/register.html', accounts=ganache_accounts)
        except Exception as e:
            flash('Private Key tidak valid!', 'danger')
            return render_template('auth/register.html', accounts=ganache_accounts)

        if User.query.filter_by(email=email).first():
            flash('Email sudah terdaftar.', 'danger')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Simpan User beserta Wallet & Private Key
        user = User(
            username=username, 
            email=email, 
            password=hashed_password, 
            role=role, 
            wallet_address=wallet,
            private_key=p_key 
        )
        db.session.add(user)
        db.session.commit()
        flash(f'Akun berhasil dibuat! Wallet {wallet[:6]}... terhubung.', 'success')
        return redirect(url_for('login'))
        
    return render_template('auth/register.html', accounts=ganache_accounts)

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
            flash('Login berhasil!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login gagal. Cek email dan password.', 'danger')
    return render_template('auth/login.html')

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    try:
        count = contract.functions.getCampaignCount().call()
        campaigns = []
        for i in range(count - 1, -1, -1):
            try:
                camp = contract.functions.getCampaign(i).call()
                db_data = CampaignData.query.get(i)
                image_file = db_data.image_filename if db_data and db_data.image_filename else None
                
                campaign_data = {
                    'id': i,
                    'title': camp[1],
                    'deadline': datetime.fromtimestamp(camp[2]).strftime('%d %b %Y'),
                    'amount_raised': web3.from_wei(camp[3], 'ether'),
                    'is_active': (camp[2] > time.time()) and (camp[4] == 1),
                    'image': image_file
                }
                campaigns.append(campaign_data)
            except Exception:
                continue
        return render_template('index.html', campaigns=campaigns)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/ui/create", methods=["GET", "POST"])
@login_required
def ui_create():
    if current_user.role not in ['creator', 'admin']:
        flash('Hanya Kreator yang dapat membuat kampanye.', 'danger')
        return redirect(url_for('index'))

    if request.method == "POST":
        try:
            title = request.form.get("title")
            duration = int(request.form.get("duration"))
            description = request.form.get("description")
            
            # [OTOMATIS] Ambil kredensial dari User yang Login
            wallet_from = current_user.wallet_address
            private_key = current_user.private_key

            filename = None
            if 'evidence_image' in request.files:
                file = request.files['evidence_image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filename = f"{int(time.time())}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            current_id = contract.functions.getCampaignCount().call()
            
            tx = contract.functions.createCampaign(title, duration).build_transaction({
                "from": wallet_from, 
                "nonce": web3.eth.get_transaction_count(wallet_from),
                "gas": 3000000,
                "gasPrice": web3.eth.gas_price
            })
            
            signed_tx = web3.eth.account.sign_transaction(tx, private_key=private_key)
            web3.eth.send_raw_transaction(signed_tx[0])

            new_campaign_data = CampaignData(
                id=current_id,
                description=description,
                image_filename=filename
            )
            db.session.add(new_campaign_data)
            db.session.commit()

            flash(f'Sukses! Kampanye diterbitkan oleh {wallet_from[:6]}...', 'success')
            return redirect(url_for('index'))
        
        except Exception as e:
            print(f"ERROR: {e}")
            flash(f'Gagal: {str(e)}', 'danger')

    return render_template("create_campaign.html")

@app.route("/ui/campaign/<int:id>")
def campaign_detail(id):
    try:
        c = contract.functions.getCampaign(id).call()
        db_data = CampaignData.query.get(id)
        
        data = {
            "id": id,
            "creator": c[0],
            "title": c[1],
            "deadline": datetime.fromtimestamp(c[2]).strftime('%d %b %Y %H:%M'),
            "totalDonations": web3.from_wei(c[3], 'ether'),
            "status_code": c[4],
            "status_label": get_status_label(c[4]),
            "is_active": (c[2] > time.time()) and (c[4] == 1),
            "description": db_data.description if db_data else "Tidak ada deskripsi.",
            "image": db_data.image_filename if db_data else None
        }
        return render_template("campaign_detail.html", c=data)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/ui/donate/<int:id>", methods=["GET", "POST"])
@login_required
def donate_page(id):
    try:
        c = contract.functions.getCampaign(id).call()
        data = {"id": id, "title": c[1], "totalDonations": web3.from_wei(c[3], 'ether')}
        
        if request.method == "POST":
            # [OTOMATIS] Gunakan wallet user yang login
            wallet_from = current_user.wallet_address
            private_key = current_user.private_key
            
            amount_wei = web3.to_wei(request.form["amount"], "ether")
            
            tx = contract.functions.donateToCampaign(id).build_transaction({
                "from": wallet_from,
                "value": amount_wei,
                "nonce": web3.eth.get_transaction_count(wallet_from),
                "gas": 3000000,
                "gasPrice": web3.eth.gas_price
            })
            signed_tx = web3.eth.account.sign_transaction(tx, private_key=private_key)
            web3.eth.send_raw_transaction(signed_tx[0])
            
            flash('Donasi berhasil dikirim!', 'success')
            return redirect(url_for('campaign_detail', id=id))

        return render_template("donate_page.html", c=data)
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/ui/admin")
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('index'))
    
    total = contract.functions.getCampaignCount().call()
    data = []
    for i in range(total):
        c = contract.functions.getCampaign(i).call()
        data.append({
            "id": i, "creator": c[0], "title": c[1],
            "deadline": datetime.fromtimestamp(c[2]).strftime('%d/%m/%Y'),
            "totalDonations": web3.from_wei(c[3], 'ether'),
            "status_label": get_status_label(c[4]), "status_code": c[4]
        })
    return render_template("admin_dashboard.html", campaigns=data)

@app.route("/ui/admin/action/<string:action>/<int:id>", methods=["POST"])
@login_required
def admin_action(action, id):
    if current_user.role != 'admin': return "Unauthorized", 403
    
    # [OTOMATIS] Gunakan wallet admin yang sedang login
    sender = current_user.wallet_address
    pk = current_user.private_key

    try:
        if action == "approve": func = contract.functions.approveCampaign(id)
        elif action == "reject": func = contract.functions.rejectCampaign(id)
        elif action == "disable": func = contract.functions.disableCampaign(id)
        else: return "Invalid"
        
        tx = func.build_transaction({
            "from": sender, "nonce": web3.eth.get_transaction_count(sender),
            "gas": 3000000, "gasPrice": web3.eth.gas_price
        })
        signed = web3.eth.account.sign_transaction(tx, private_key=pk)
        web3.eth.send_raw_transaction(signed[0])
        
        flash(f'Sukses {action} campaign #{id}', 'success')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Gagal: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

# ============================
# INISIALISASI DATABASE & ADMIN
# ============================
if __name__ == "__main__":
    with app.app_context():
        # Buat tabel jika belum ada
        db.create_all()
        
        # Cek apakah admin sudah ada
        admin_user = User.query.filter_by(role='admin').first()
        
        if not admin_user:
            print("⚠️  Admin belum ditemukan. Membuat akun Admin Default...")
            
            # Hash password 'admin123'
            hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
            
            # Masukkan Alamat Wallet Ganache Pertama Anda di sini!
            # Contoh: 0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1
            default_admin_wallet = "0x66F8CE73Ec218656C2964cb237e94def2265eD46" 
            
            # Masukkan Private Key Ganache Pertama Anda di sini!
            default_admin_pk = "0x6e1d791d52bbee062830c59a0b5f87a6afb3c6bece1a7699b6a0b044f6724b25"

            default_admin = User(
                username='SuperAdmin',
                email='admin@platform.com',
                password=hashed_pw,
                role='admin',
                wallet_address=default_admin_wallet,
                private_key=default_admin_pk
            )
            
            try:
                db.session.add(default_admin)
                db.session.commit()
                print("✅ Akun Admin Default Berhasil Dibuat!")
                print("   Email:    admin@platform.com")
                print("   Password: admin123")
                print("   Wallet:  ", default_admin_wallet)
            except Exception as e:
                print(f"❌ Gagal membuat admin: {e}")
        else:
            print("✅ Akun Admin sudah tersedia di database.")

    # Jalankan server
    app.run(debug=True, port=5000)