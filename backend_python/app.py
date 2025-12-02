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

# --- FUNGSI FETCH BERITA (MULTI-SOURCE AGGREGATOR) ---
def get_humanitarian_news():
    rss_sources = [
        {"url": "https://www.antaranews.com/rss/humaniora.xml", "name": "Antara News"},
        {"url": "https://www.cnnindonesia.com/nasional/rss", "name": "CNN Indonesia"},
        {"url": "https://www.republika.co.id/rss/nasional/umum", "name": "Republika"},
        {"url": "https://www.viva.co.id/rss/berita/nasional", "name": "Viva News"}
    ]
    keywords = ["banjir", "gempa", "longsor", "kebakaran", "bencana", "tsunami", "korban", "bantuan", "donasi", "miskin", "sosial"]
    aggregated_news = []
    
    for source in rss_sources:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:5]:
                title = entry.title.lower()
                summary = entry.summary.lower() if hasattr(entry, 'summary') else ""
                if any(k in title for k in keywords) or any(k in summary for k in keywords):
                    pub_time = entry.published_parsed if hasattr(entry, 'published_parsed') else time.gmtime()
                    timestamp = mktime(pub_time) if pub_time else 0
                    aggregated_news.append({
                        'title': entry.title,
                        'link': entry.link,
                        'published': entry.published if hasattr(entry, 'published') else "Baru saja",
                        'timestamp': timestamp,
                        'summary': summary[:100] + "...",
                        'source': source["name"]
                    })
        except Exception:
            continue

    aggregated_news.sort(key=lambda x: x['timestamp'], reverse=True)
    final_news = aggregated_news[:4]
        
    if not final_news:
        final_news = [
            {'title': 'Banjir Bandang Terjang Pemukiman Warga', 'link': '#', 'published': 'Hari ini', 'summary': 'Warga butuh bantuan...', 'source': 'Simulasi'},
            {'title': 'Gempa M 5.6 Guncang Wilayah Cianjur', 'link': '#', 'published': 'Kemarin', 'summary': 'Kerusakan infrastruktur...', 'source': 'Simulasi'}
        ]
    return final_news

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
    return render_template('profile.html', user=user, balance=balance, days_wait=0)

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
            for i in range(count):
                c = contract.functions.getCampaign(i).call()
                status_code = c[8]; creator_address = c[1]
                is_owner = (creator_address == session.get('wallet'))
                should_show = False
                if status_code == 1: should_show = True
                elif is_owner: should_show = True
                if status_code == 3: should_show = False
                
                if should_show:
                    status_label = 'Pending' if status_code == 0 else 'Active' if status_code == 1 else 'Rejected'
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
    
    if request.method == 'POST':
        title = request.form['title']; desc = request.form['description']
        target = float(request.form['target'])
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
            
            # 1. Ambil Nonce
            nonce = web3.eth.get_transaction_count(user_data['wallet_address'])
            
            txn = contract.functions.createCampaign(title, desc, target_wei, filename, 43200).build_transaction({
                'chainId': web3.eth.chain_id, 'gas': 2000000, 'gasPrice': web3.eth.gas_price, 'nonce': nonce
            })
            signed_txn = web3.eth.account.sign_transaction(txn, private_key=user_data['private_key'])
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            web3.eth.wait_for_transaction_receipt(tx_hash)
            
            new_count = contract.functions.getCampaignCount().call()
            conn.execute('INSERT INTO campaign_details (blockchain_id, category, usage_plan, social_link, tagline) VALUES (?, ?, ?, ?, ?)',
                         (new_count - 1, category, usage_plan, social_link, tagline))
            conn.commit(); conn.close()
            flash(f"Campaign berhasil dibuat! Nonce Transaksi: {nonce}", "success")
            return redirect(url_for('dashboard'))
        except Exception as e: conn.close(); flash(f"Error Blockchain: {str(e)}", "error")
    return render_template('create_campaign.html')

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
        amount_eth = float(amount); amount_wei = web3.to_wei(amount_eth, 'ether')
        conn = get_db_connection(); user_data = conn.execute("SELECT wallet_address, private_key, username FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        
        # 1. Ambil Nonce Terbaru
        nonce = web3.eth.get_transaction_count(user_data['wallet_address'])
        
        txn = contract.functions.donateToCampaign(id).build_transaction({
            'chainId': web3.eth.chain_id, 'gas': 2000000, 'gasPrice': web3.eth.gas_price, 'nonce': nonce, 'value': amount_wei 
        })
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=user_data['private_key'])
        
        # Kirim Tx
        tx_hash_bytes = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash_bytes)
        tx_hash_str = tx_hash_bytes.hex()
        
        # 2. Simpan ke Database (UPDATE: simpan nonce dan hash)
        conn.execute('''INSERT INTO donations (blockchain_id, donor_name, amount, message, timestamp, tx_hash, nonce) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (id, user_data['username'], amount, message, datetime.now().strftime("%d %b %Y, %H:%M"), tx_hash_str, nonce))
        
        conn.commit(); conn.close()
        flash(f"Terima kasih! Donasi berhasil. Nonce: #{nonce}", "success")
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
        # 1. Ambil Nonce
        nonce = web3.eth.get_transaction_count(user_data['wallet_address'])
        
        txn = contract.functions.withdrawFunds(id).build_transaction({
            'chainId': web3.eth.chain_id, 'gas': 2000000, 'gasPrice': web3.eth.gas_price, 'nonce': nonce
        })
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=user_data['private_key'])
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash)
        flash(f"Dana berhasil ditarik! Nonce Transaksi: #{nonce}", "success")
    except Exception as e: flash(f"Gagal Tarik Dana: {e}", "error")
    return redirect(url_for('campaign_detail', id=id))

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
            details_map = {d['blockchain_id']: d for d in db_details}
            
            for i in range(count):
                c = contract.functions.getCampaign(i).call()
                status_code = c[8]; creator_addr = c[1]
                if status_code == 0: stats['pending'] += 1
                elif status_code == 1: stats['active'] += 1
                elif status_code == 2: stats['rejected'] += 1
                elif status_code == 3: stats['deleted'] += 1
                
                campaigns_data.append({
                    'id': c[0], 'title': c[2],
                    'creator_name': get_username_by_wallet(creator_addr),
                    'creator_addr': creator_addr,
                    'target': web3.from_wei(c[4], 'ether'),
                    'status_code': status_code,
                    'status': 'Pending' if status_code==0 else 'Active' if status_code==1 else 'Rejected'
                })
        except: pass

    transactions_log = get_all_transactions()
    ganache_accounts = []; recent_blocks = []; network_status = "Offline"
    
    try:
        if web3 and web3.is_connected():
            network_status = "Connected to Ganache"
            for i, acc in enumerate(web3.eth.accounts):
                bal = web3.from_wei(web3.eth.get_balance(acc), 'ether')
                ganache_accounts.append({'index': i, 'address': acc, 'balance': "{:.4f}".format(bal)})
            latest = web3.eth.block_number
            for i in range(latest, max(-1, latest - 10), -1):
                blk = web3.eth.get_block(i)
                recent_blocks.append({
                    'number': blk.number, 'hash': blk.hash.hex(),
                    'tx_count': len(blk.transactions),
                    'timestamp': datetime.fromtimestamp(blk.timestamp).strftime('%H:%M:%S')
                })
    except: network_status = "Error Network"

    conn.close()
    return render_template('admin_dashboard.html', stats=stats, total_users=len(users_rows),
                           campaigns=campaigns_data, users=users_rows, transactions=transactions_log,
                           ganache_accounts=ganache_accounts, recent_blocks=recent_blocks, network_status=network_status)

@app.route('/admin/approve/<int:id>')
def approve_campaign(id):
    if session.get('role') != 'admin': return redirect(url_for('index'))
    try:
        tx = contract.functions.approveCampaign(id).transact({'from': web3.eth.accounts[0]})
        web3.eth.wait_for_transaction_receipt(tx); flash(f"Campaign #{id} Approved!", "success")
    except: flash("Gagal approve", "error")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_campaign/<int:id>')
def delete_campaign(id):
    if session.get('role') != 'admin': return redirect(url_for('index'))
    try:
        tx = contract.functions.deleteCampaign(id).transact({'from': web3.eth.accounts[0]})
        web3.eth.wait_for_transaction_receipt(tx); flash(f"Campaign #{id} Deleted.", "success")
    except: flash("Gagal hapus", "error")
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
    return render_template('404.html'), 404

@app.route('/explorer')
def explorer():
    return render_template('explorer.html')

@app.route('/api/explorer-data')
def explorer_data_api():
    conn = get_db_connection()
    
    # 1. Ambil 15 Transaksi Terakhir
    query = '''
        SELECT d.amount, d.timestamp, d.tx_hash, d.nonce, u.wallet_address 
        FROM donations d
        JOIN users u ON d.donor_name = u.username
        ORDER BY d.id DESC LIMIT 15
    '''
    tx_rows = conn.execute(query).fetchall()
    
    transactions = []
    for tx in tx_rows:
        transactions.append({
            'hash': tx['tx_hash'],
            'from': tx['wallet_address'],
            'amount': tx['amount'],
            'nonce': tx['nonce'],
            'time': tx['timestamp']
        })

    # 2. Ambil SEMUA Blok dari 0 sampai Latest (Limit 100 agar tidak crash jika data banyak)
    all_blocks = []
    network_stats = {'gasPrice': 0, 'blockTime': 0, 'difficulty': 0}
    
    if web3 and web3.is_connected():
        try:
            current_block_num = web3.eth.block_number
            network_stats['gasPrice'] = web3.from_wei(web3.eth.gas_price, 'gwei')
            
            # Loop dari 0 sampai blok terakhir
            # PERINGATAN: Di production asli, ini harus dipaginasi. 
            # Untuk demo Ganache (biasanya <100 blok), ini aman.
            for i in range(0, current_block_num + 1):
                blk = web3.eth.get_block(i)
                all_blocks.append({
                    'number': blk.number,
                    'hash': blk.hash.hex(),
                    'parentHash': blk.parentHash.hex(),
                    'tx_count': len(blk.transactions),
                    'timestamp': datetime.fromtimestamp(blk.timestamp).strftime('%H:%M:%S'),
                    'gasUsed': blk.gasUsed,
                    'miner': blk.miner
                })
        except: pass
    
    conn.close()
    
    return {'transactions': transactions, 'blocks': all_blocks, 'stats': network_stats}

if __name__ == '__main__':
    app.run(debug=True, port=5000)