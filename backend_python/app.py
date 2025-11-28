from flask import Flask, render_template, request, redirect, url_for, session, flash
from web3 import Web3
import sqlite3
import os
import time
from datetime import datetime, timedelta
import feedparser
from time import mktime

# --- KONFIGURASI ---
app = Flask(__name__)
app.secret_key = 'rahasia_donasi_blockchain'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Import Contract Data
try:
    from contract_data import contract, web3
except ImportError:
    contract = None
    web3 = None
    print("Warning: contract_data.py tidak ditemukan. Fitur blockchain tidak aktif.")

# --- 1. CONTEXT PROCESSOR ---
@app.context_processor
def inject_blockchain_status():
    status = {
        'connected': False,
        'user_balance': '0.0000',
        'gas_price': '0',
        'block_number': '0'
    }
    try:
        if web3 and web3.is_connected():
            status['connected'] = True
            status['block_number'] = web3.eth.block_number
            gas_wei = web3.eth.gas_price
            status['gas_price'] = "{:.1f}".format(web3.from_wei(gas_wei, 'gwei'))
            
            if 'wallet' in session:
                try:
                    bal_wei = web3.eth.get_balance(session['wallet'])
                    bal_eth = web3.from_wei(bal_wei, 'ether')
                    status['user_balance'] = "{:.4f}".format(float(bal_eth))
                except:
                    status['user_balance'] = "Err"
    except Exception as e:
        pass
    return dict(bc_stat=status)

# --- 2. DATABASE SETUP ---
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

    c.execute('''CREATE TABLE IF NOT EXISTS donations 
                 (id INTEGER PRIMARY KEY, blockchain_id INTEGER, 
                  donor_name TEXT, amount REAL, message TEXT, timestamp TEXT)''')
    
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
            events = contract.events.DonationReceived().get_logs(fromBlock=0)
            for e in events:
                args = e['args']
                logs.append({
                    'type': 'Donasi Masuk',
                    'campaign_id': args['campaignId'],
                    'from': get_username_by_wallet(args['donor']),
                    'from_addr': args['donor'],
                    'amount': web3.from_wei(args['amount'], 'ether'),
                    'timestamp': time.ctime(args['timestamp'])
                })
            
            events_created = contract.events.CampaignCreated().get_logs(fromBlock=0)
            for e in events_created:
                args = e['args']
                logs.append({
                    'type': 'Campaign Dibuat',
                    'campaign_id': args['id'],
                    'from': get_username_by_wallet(args['creator']),
                    'from_addr': args['creator'],
                    'amount': '-',
                    'timestamp': time.ctime(args['timestamp'])
                })
            logs.sort(key=lambda x: x['timestamp'], reverse=True)
    except Exception as e:
        print(f"Error fetching logs: {e}")
    return logs

# --- FUNGSI FETCH BERITA (MULTI-SOURCE AGGREGATOR) ---
def get_humanitarian_news():
    # Daftar Sumber RSS Terpercaya
    rss_sources = [
        {"url": "https://www.antaranews.com/rss/humaniora.xml", "name": "Antara News"},
        {"url": "https://www.cnnindonesia.com/nasional/rss", "name": "CNN Indonesia"},
        {"url": "https://www.republika.co.id/rss/nasional/umum", "name": "Republika"},
        {"url": "https://www.viva.co.id/rss/berita/nasional", "name": "Viva News"}
    ]
    
    # Kata Kunci Filter (Trigger Words)
    keywords = [
        "banjir", "gempa", "longsor", "kebakaran", "bencana", "tsunami", "erupsi",
        "korban", "pengungsi", "bantuan", "donasi", "miskin", "kelaparan",
        "difabel", "panti", "sosial", "kemanusiaan", "zakat", "galang dana",
        "medis", "sakit", "warga", "desa", "peduli", "dampak", "rusak"
    ]
    
    aggregated_news = []
    
    for source in rss_sources:
        try:
            feed = feedparser.parse(source["url"])
            # Loop maksimal 10 berita per sumber untuk efisiensi
            for entry in feed.entries[:10]:
                title = entry.title.lower()
                summary = entry.summary.lower() if hasattr(entry, 'summary') else ""
                
                # Cek Relevansi
                if any(k in title for k in keywords) or any(k in summary for k in keywords):
                    # Bersihkan summary
                    clean_summary = entry.summary.split('<')[0] if hasattr(entry, 'summary') else entry.title
                    
                    # Ambil Waktu Publish (Unix Timestamp untuk sorting)
                    pub_time = entry.published_parsed if hasattr(entry, 'published_parsed') else time.gmtime()
                    timestamp = mktime(pub_time) if pub_time else 0
                    
                    aggregated_news.append({
                        'title': entry.title,
                        'link': entry.link,
                        'published': entry.published if hasattr(entry, 'published') else "Baru saja",
                        'timestamp': timestamp, # Untuk sorting
                        'summary': clean_summary,
                        'source': source["name"]
                    })
        except Exception as e:
            print(f"Skip source {source['name']}: {e}")
            continue

    # Sorting: Urutkan dari yang paling baru (timestamp terbesar)
    aggregated_news.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Ambil 4 Teratas
    final_news = aggregated_news[:4]
        
    # FALLBACK MOCK DATA (Jika internet mati atau tidak ada berita relevan)
    if not final_news:
        final_news = [
            {
                'title': 'Banjir Bandang Terjang Pemukiman Warga, Ribuan Mengungsi', 
                'link': '#', 'published': 'Hari ini', 
                'summary': 'Hujan deras menyebabkan tanggul jebol. Warga membutuhkan bantuan logistik...', 
                'source': 'Simulasi Bencana'
            },
            {
                'title': 'Gempa M 5.6 Guncang Wilayah Cianjur, Rumah Rusak Berat', 
                'link': '#', 'published': 'Kemarin', 
                'summary': 'Gempa darat dangkal menyebabkan kerusakan infrastruktur...', 
                'source': 'Simulasi Bencana'
            },
            {
                'title': 'Kebakaran Hanguskan Ratusan Rumah di Kawasan Padat', 
                'link': '#', 'published': '2 Hari lalu', 
                'summary': 'Api dengan cepat menyebar. Warga kehilangan tempat tinggal...', 
                'source': 'Simulasi Bencana'
            },
            {
                'title': 'Krisis Air Bersih di Desa Terpencil Akibat Kemarau', 
                'link': '#', 'published': '3 Hari lalu', 
                'summary': 'Sumur warga kering. Mereka terpaksa berjalan jauh demi air...', 
                'source': 'Simulasi Sosial'
            }
        ]
        
    return final_news

# --- 4. ROUTES (HALAMAN UTAMA UPDATE) ---

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

# --- 5. ROUTES (AUTH & PROFILE) ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']; password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']; session['username'] = user['username']
            session['role'] = user['role']; session['wallet'] = user['wallet_address']
            session['profile_pic'] = user['profile_pic'] if user['profile_pic'] else 'default_user.png'
            return redirect(url_for('dashboard'))
        else: flash('Login gagal! Cek email/password.', 'error')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    ganache_accounts = []
    if web3 and web3.is_connected():
        try: ganache_accounts = web3.eth.accounts
        except: pass
    if request.method == 'POST':
        username = request.form['username']; email = request.form['email']
        password = request.form['password']; role = request.form['role']
        wallet = request.form['wallet_address']; pk = request.form['private_key']
        
        if web3 and not Web3.is_address(wallet):
            flash('Alamat Wallet Ethereum tidak valid!', 'error')
            return render_template('auth/register.html', accounts=ganache_accounts)

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, email, password, role, wallet_address, private_key, profile_pic) VALUES (?, ?, ?, ?, ?, ?, ?)',
                         (username, email, password, role, wallet, pk, 'default_user.png'))
            conn.commit()
            flash('Registrasi berhasil! Setup Wallet selesai.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email atau Username sudah terdaftar.', 'error')
        except Exception as e:
            flash(f'Gagal Register: {e}', 'error')
        finally: conn.close()
    return render_template('auth/register.html', accounts=ganache_accounts)

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
            last_change = user['last_username_change']
            can_change = True
            if last_change:
                last_date = datetime.strptime(last_change, '%Y-%m-%d %H:%M:%S')
                if datetime.now() < last_date + timedelta(days=14):
                    can_change = False; days_left = (last_date + timedelta(days=14) - datetime.now()).days
                    flash(f"Gagal: Username hanya bisa diubah 14 hari sekali. Tunggu {days_left} hari lagi.", "error")
            if can_change:
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
    days_until_change = 0
    if user['last_username_change']:
        last_date = datetime.strptime(user['last_username_change'], '%Y-%m-%d %H:%M:%S')
        delta = (last_date + timedelta(days=14)) - datetime.now()
        if delta.days > 0: days_until_change = delta.days
    balance = "0"
    try: 
        if web3: balance = "{:.4f}".format(web3.from_wei(web3.eth.get_balance(user['wallet_address']), 'ether'))
    except: pass
    conn.close()
    return render_template('profile.html', user=user, balance=balance, days_wait=days_until_change)

# --- 6. ROUTES (CAMPAIGN) ---

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
            for i in range(count):
                c = contract.functions.getCampaign(i).call()
                status_code = c[8]; creator_address = c[1]
                is_owner = (creator_address == session.get('wallet'))
                should_show = False
                if status_code == 1: should_show = True
                elif is_owner: should_show = True
                if status_code == 3: should_show = False
                if should_show:
                    status_label = 'Unknown'
                    if status_code == 0: status_label = 'Pending'
                    elif status_code == 1: status_label = 'Active'
                    elif status_code == 2: status_label = 'Rejected'
                    elif status_code == 3: status_label = 'Deleted'
                    detail = details_map.get(c[0])
                    campaigns.append({
                        'id': c[0], 'title': c[2], 'desc': c[3],
                        'target': web3.from_wei(c[4], 'ether'),
                        'collected': web3.from_wei(c[5], 'ether'),
                        'image': c[6], 'status_code': status_code,
                        'status_label': status_label, 'is_owner': is_owner,
                        'tagline': detail['tagline'] if detail else c[3][:50] + "...",
                        'category': detail['category'] if detail else "Umum"
                    })
        except Exception as e: print(f"Dashboard Error: {e}")
    return render_template('campaigns.html', campaigns=campaigns)

@app.route('/create_campaign', methods=['GET', 'POST'])
def create_campaign():
    if 'user_id' not in session: flash("Silakan login terlebih dahulu.", "error"); return redirect(url_for('login'))
    if session.get('role') != 'kreator': flash("Hanya akun KREATOR yang bisa membuat kampanye!", "error"); return redirect(url_for('dashboard'))
    prefill_title = request.args.get('title', '')
    if request.method == 'POST':
        title = request.form['title']; desc = request.form['description']
        target = float(request.form['target'])
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
        if user_data is None or not user_data['wallet_address'] or not user_data['private_key']:
            conn.close(); flash("Error: Data akun tidak lengkap.", "error"); return redirect(url_for('dashboard'))
        try:
            target_wei = web3.to_wei(target, 'ether'); duration_minutes = duration_days * 1440 
            nonce = web3.eth.get_transaction_count(user_data['wallet_address'])
            txn = contract.functions.createCampaign(title, desc, target_wei, filename, duration_minutes).build_transaction({
                'chainId': web3.eth.chain_id, 'gas': 2000000, 'gasPrice': web3.eth.gas_price, 'nonce': nonce
            })
            signed_txn = web3.eth.account.sign_transaction(txn, private_key=user_data['private_key'])
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            web3.eth.wait_for_transaction_receipt(tx_hash)
            new_count = contract.functions.getCampaignCount().call()
            conn.execute('INSERT INTO campaign_details (blockchain_id, category, usage_plan, social_link, tagline) VALUES (?, ?, ?, ?, ?)',
                         (new_count - 1, category, usage_plan, social_link, tagline))
            conn.commit(); conn.close()
            flash(f"Campaign '{title}' berhasil dibuat! Menunggu Admin.", "success"); return redirect(url_for('dashboard'))
        except Exception as e: conn.close(); flash(f"Error Blockchain: {str(e)}", "error")
    return render_template('create_campaign.html', prefill_title=prefill_title)

@app.route('/campaign/<int:id>')
def campaign_detail(id):
    try:
        c = contract.functions.getCampaign(id).call()
        conn = get_db_connection()
        detail = conn.execute("SELECT * FROM campaign_details WHERE blockchain_id = ?", (id,)).fetchone()
        updates = conn.execute("SELECT * FROM campaign_updates WHERE blockchain_id = ? ORDER BY id DESC", (id,)).fetchall()
        donations = conn.execute("SELECT * FROM donations WHERE blockchain_id = ? ORDER BY id DESC", (id,)).fetchall()
        conn.close()
        target = web3.from_wei(c[4], 'ether'); collected = web3.from_wei(c[5], 'ether')
        percent = (float(collected) / float(target) * 100) if float(target) > 0 else 0
        status_map = {0: 'Pending', 1: 'Active', 2: 'Rejected', 3: 'Deleted'}
        creator_name = get_username_by_wallet(c[1])
        campaign = {
            'id': c[0], 'creator': c[1], 'creator_name': creator_name,
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
    if session.get('role') != 'donatur': flash("Hanya akun DONATUR yang bisa berdonasi!", "error"); return redirect(url_for('campaign_detail', id=id))
    amount = request.form.get('amount'); message = request.form.get('message')
    try:
        amount_eth = float(amount); amount_wei = web3.to_wei(amount_eth, 'ether')
        conn = get_db_connection(); user_data = conn.execute("SELECT wallet_address, private_key, username FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        if not user_data['private_key']: flash("Error: Private Key tidak ditemukan.", "error"); conn.close(); return redirect(url_for('campaign_detail', id=id))
        nonce = web3.eth.get_transaction_count(user_data['wallet_address'])
        txn = contract.functions.donateToCampaign(id).build_transaction({
            'chainId': web3.eth.chain_id, 'gas': 2000000, 'gasPrice': web3.eth.gas_price, 'nonce': nonce, 'value': amount_wei 
        })
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=user_data['private_key'])
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash)
        conn.execute('INSERT INTO donations (blockchain_id, donor_name, amount, message, timestamp) VALUES (?, ?, ?, ?, ?)',
                     (id, user_data['username'], amount, message, datetime.now().strftime("%d %b %Y, %H:%M")))
        conn.commit(); conn.close()
        flash(f"Terima kasih! Donasi {amount} ETH berhasil dikirim.", "success")
    except Exception as e: flash(f"Gagal Donasi: {e}", "error")
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
    conn.commit(); conn.close()
    flash("Kabar terbaru berhasil diposting!", "success"); return redirect(url_for('campaign_detail', id=id))

@app.route('/withdraw/<int:id>')
def withdraw_funds(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection(); user_data = conn.execute("SELECT wallet_address, private_key FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    try:
        nonce = web3.eth.get_transaction_count(user_data['wallet_address'])
        txn = contract.functions.withdrawFunds(id).build_transaction({
            'chainId': web3.eth.chain_id, 'gas': 2000000, 'gasPrice': web3.eth.gas_price, 'nonce': nonce
        })
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=user_data['private_key'])
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash)
        flash("Dana berhasil ditarik ke dompet Anda!", "success")
    except Exception as e: flash(f"Gagal Tarik Dana: {e}", "error")
    return redirect(url_for('campaign_detail', id=id))

# --- 8. ADMIN PANEL ---
@app.route('/admin')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin': return "Akses Ditolak"
    campaigns = []; stats = {'pending': 0, 'active': 0, 'rejected': 0, 'deleted': 0, 'total_campaigns': 0}
    if contract:
        count = contract.functions.getCampaignCount().call()
        stats['total_campaigns'] = count
        for i in range(count):
            c = contract.functions.getCampaign(i).call()
            status_map = {0: 'Pending', 1: 'Approved', 2: 'Rejected', 3: 'Deleted'}
            if c[8] == 0: stats['pending'] += 1
            elif c[8] == 1: stats['active'] += 1
            elif c[8] == 2: stats['rejected'] += 1
            elif c[8] == 3: stats['deleted'] += 1
            campaigns.append({
                'id': c[0], 'creator_addr': c[1], 'creator_name': get_username_by_wallet(c[1]),
                'title': c[2], 'target': web3.from_wei(c[4], 'ether'),
                'status': status_map[c[8]], 'status_code': c[8]
            })
    conn = get_db_connection(); users = conn.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
    conn.close(); transactions = get_all_transactions() 
    return render_template('admin_dashboard.html', campaigns=campaigns, users=users, transactions=transactions, stats=stats, total_users=len(users))

@app.route('/admin/approve/<int:id>')
def approve_campaign(id):
    try:
        tx = contract.functions.approveCampaign(id).transact({'from': web3.eth.accounts[0]})
        web3.eth.wait_for_transaction_receipt(tx); flash(f"Campaign #{id} Approved!", "success")
    except: flash("Gagal approve", "error")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_campaign/<int:id>')
def delete_campaign(id):
    try:
        tx = contract.functions.deleteCampaign(id).transact({'from': web3.eth.accounts[0]})
        web3.eth.wait_for_transaction_receipt(tx); flash(f"Campaign #{id} Deleted.", "success")
    except: flash("Gagal hapus", "error")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    try:
        conn = get_db_connection(); conn.execute('DELETE FROM users WHERE id = ?', (user_id,)); conn.commit(); conn.close()
        flash(f"User ID {user_id} dihapus.", "success")
    except: flash("Gagal hapus user", "error")
    return redirect(url_for('admin_dashboard'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)