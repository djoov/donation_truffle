from flask import Flask, render_template, request, redirect, url_for, session, flash
from web3 import Web3
from contract_data import contract, web3, get_contract_info 
import sqlite3
import os
import time

app = Flask(__name__)
app.secret_key = 'rahasia_donasi_blockchain'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# --- CONTEXT PROCESSOR ---
@app.context_processor
def inject_blockchain_status():
    status = {'connected': False, 'user_balance': '0.0000', 'gas_price': '0', 'block_number': '0'}
    try:
        if web3.is_connected():
            status['connected'] = True
            status['block_number'] = web3.eth.block_number
            status['gas_price'] = "{:.1f}".format(web3.from_wei(web3.eth.gas_price, 'gwei'))
            if 'wallet' in session:
                try:
                    bal = web3.from_wei(web3.eth.get_balance(session['wallet']), 'ether')
                    status['user_balance'] = "{:.4f}".format(float(bal))
                except: status['user_balance'] = "Err"
    except: pass
    return dict(bc_stat=status)

# --- DATABASE SETUP  ---
def init_db():
    if not os.path.exists('instance'): os.makedirs('instance')
    conn = sqlite3.connect('instance/users.db')
    c = conn.cursor()
    
    # Tabel Users
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, username TEXT, email TEXT, 
                  password TEXT, role TEXT, wallet_address TEXT, private_key TEXT)''')
    
    # Tabel Campaign Details (Data Pelengkap Off-Chain)
    c.execute('''CREATE TABLE IF NOT EXISTS campaign_details 
                 (id INTEGER PRIMARY KEY, 
                  blockchain_id INTEGER, 
                  category TEXT, 
                  usage_plan TEXT, 
                  social_link TEXT,
                  tagline TEXT)''')
    
    # Admin Default
    c.execute("SELECT * FROM users WHERE role='admin'")
    if not c.fetchone():
        try: admin_wallet = web3.eth.accounts[0]
        except: admin_wallet = "0x00"
        c.execute("INSERT INTO users (username, email, password, role, wallet_address, private_key) VALUES (?, ?, ?, ?, ?, ?)",
                  ('SuperAdmin', 'admin@donasi.com', 'admin123', 'admin', admin_wallet, 'ADMIN_KEY'))
    conn.commit()
    conn.close()

init_db()

# --- HELPER ---
def get_db_connection():
    conn = sqlite3.connect('instance/users.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_username_by_wallet(wallet_addr):
    conn = get_db_connection()
    user = conn.execute('SELECT username FROM users WHERE wallet_address = ?', (wallet_addr,)).fetchone()
    conn.close()
    return user['username'] if user else "Unknown"

# --- ROUTES ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/help')
def help_page(): return render_template('help.html')

@app.route('/how-it-works')
def how_it_works_page():
    return render_template('how_it_works.html')

@app.route('/privacy')
def privacy_page():
    return render_template('privacy.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']; session['username'] = user['username']
            session['role'] = user['role']; session['wallet'] = user['wallet_address']
            return redirect(url_for('dashboard'))
        else: flash('Login gagal!')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    ganache_accounts = []
    if web3.is_connected():
        try: ganache_accounts = web3.eth.accounts
        except: pass

    if request.method == 'POST':
        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO users (username, email, password, role, wallet_address, private_key) VALUES (?, ?, ?, ?, ?, ?)',
                         (request.form['username'], request.form['email'], request.form['password'], 
                          request.form['role'], request.form['wallet_address'], request.form['private_key']))
            conn.commit()
            flash('Registrasi berhasil!')
            return redirect(url_for('login'))
        except Exception as e: flash(f'Gagal Register: {e}')
        finally: conn.close()
    return render_template('auth/register.html', accounts=ganache_accounts)

@app.route('/dashboard')
def dashboard():
    if session.get('role') == 'admin': return redirect(url_for('admin_dashboard'))
    campaigns = []
    if contract:
        count = contract.functions.getCampaignCount().call()
        
        # Ambil data off-chain
        conn = get_db_connection()
        details_rows = conn.execute("SELECT * FROM campaign_details").fetchall()
        conn.close()
        details_map = {d['blockchain_id']: d for d in details_rows}

        for i in range(count):
            c = contract.functions.getCampaign(i).call()
            is_approved = (c[8] == 1)
            is_owner = False
            if 'wallet' in session: is_owner = (c[1] == session['wallet'])
            
            if is_approved or is_owner:
                status_label = 'Unknown'
                if c[8] == 0: status_label = 'Pending'
                elif c[8] == 1: status_label = 'Active'
                elif c[8] == 2: status_label = 'Rejected'
                elif c[8] == 3: status_label = 'Deleted'
                
                # Merge data off-chain
                detail = details_map.get(c[0])
                tagline = detail['tagline'] if detail else c[3][:50] + "..."
                category = detail['category'] if detail else "Umum"

                campaigns.append({
                    'id': c[0],
                    'title': c[2],
                    'desc': c[3],
                    'target': web3.from_wei(c[4], 'ether'),
                    'collected': web3.from_wei(c[5], 'ether'),
                    'image': c[6],
                    'status_code': c[8],
                    'status_label': status_label,
                    'is_owner': is_owner,
                    'tagline': tagline,
                    'category': category
                })
    return render_template('campaigns.html', campaigns=campaigns)

@app.route('/create_campaign', methods=['GET', 'POST'])
def create_campaign():
    if 'user_id' not in session: return redirect(url_for('login'))
    if session.get('role') != 'kreator': return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # 1. Ambil Input Dasar
        title = request.form['title']
        desc = request.form['description']
        target = float(request.form['target'])
        try: duration_days = int(request.form['duration'])
        except: duration_days = 30
        
        # 2. Ambil Input Tambahan (Off-Chain)
        category = request.form['category']
        tagline = request.form['tagline']
        usage_plan = request.form['usage_plan']
        social_link = request.form['social_link']

        # 3. Upload Gambar
        file = request.files['image']
        if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
        filename = f"{int(time.time())}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # 4. Kirim ke Blockchain
        conn = get_db_connection()
        user_data = conn.execute("SELECT wallet_address, private_key FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        
        if user_data is None:
            conn.close()
            flash("Data akun error.")
            return redirect(url_for('dashboard'))

        try:
            target_wei = web3.to_wei(target, 'ether')
            duration_minutes = duration_days * 1440 
            nonce = web3.eth.get_transaction_count(user_data['wallet_address'])
            
            txn = contract.functions.createCampaign(
                title, desc, target_wei, filename, duration_minutes 
            ).build_transaction({
                'chainId': web3.eth.chain_id, 'gas': 2000000, 
                'gasPrice': web3.eth.gas_price, 'nonce': nonce
            })
            signed_txn = web3.eth.account.sign_transaction(txn, private_key=user_data['private_key'])
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            
            # 5. Simpan Data Tambahan ke DB (Mapping ID Blockchain -> Detail Off-chain)
            # Kita harus tahu ID campaign yang baru saja dibuat. 
            # Cara paling aman: Ambil 'CampaignCount' - 1
            new_count = contract.functions.getCampaignCount().call()
            new_id = new_count - 1
            
            conn.execute('INSERT INTO campaign_details (blockchain_id, category, usage_plan, social_link, tagline) VALUES (?, ?, ?, ?, ?)',
                         (new_id, category, usage_plan, social_link, tagline))
            conn.commit()
            conn.close()

            flash(f"Campaign '{title}' berhasil dibuat!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            conn.close()
            flash(f"Error Blockchain: {str(e)}", "error")

    return render_template('create_campaign.html')

@app.route('/campaign/<int:id>')
def campaign_detail(id):
    try:
        c = contract.functions.getCampaign(id).call()
        
        # Ambil data tambahan dari DB
        conn = get_db_connection()
        detail = conn.execute("SELECT * FROM campaign_details WHERE blockchain_id = ?", (id,)).fetchone()
        conn.close()

        target = web3.from_wei(c[4], 'ether')
        collected = web3.from_wei(c[5], 'ether')
        percent = 0
        if target > 0: percent = (float(collected) / float(target)) * 100
        
        status_map = {0: 'Pending', 1: 'Active', 2: 'Rejected', 3: 'Deleted'}
        
        campaign = {
            'id': c[0],
            'creator_name': get_username_by_wallet(c[1]),
            'title': c[2],
            'desc': c[3],
            'target': target,
            'collected': collected,
            'image': c[6],
            'deadline': time.ctime(c[7]),
            'status_code': c[8],
            'percent': "{:.1f}".format(percent),
            # Data Tambahan
            'category': detail['category'] if detail else 'Umum',
            'tagline': detail['tagline'] if detail else '',
            'usage_plan': detail['usage_plan'] if detail else 'Tidak ada rincian.',
            'social_link': detail['social_link'] if detail else '#'
        }
        return render_template('campaign_detail.html', campaign=campaign)
    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/donate/<int:id>', methods=['POST'])
def donate(id):
    if session.get('role') != 'donatur':
         flash("Hanya akun DONATUR yang bisa berdonasi!")
         return redirect(url_for('campaign_detail', id=id))
    amount = request.form.get('amount')
    try:
        conn = get_db_connection()
        user_data = conn.execute("SELECT wallet_address, private_key FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        conn.close()
        
        if not user_data['private_key']: return redirect(url_for('campaign_detail', id=id))

        nonce = web3.eth.get_transaction_count(user_data['wallet_address'])
        txn = contract.functions.donateToCampaign(id).build_transaction({
            'chainId': web3.eth.chain_id, 'gas': 2000000, 'gasPrice': web3.eth.gas_price,
            'nonce': nonce, 'value': web3.to_wei(float(amount), 'ether')
        })
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=user_data['private_key'])
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash)
        flash(f"Donasi {amount} ETH berhasil!", "success")
    except Exception as e: flash(f"Gagal: {e}", "error")
    return redirect(url_for('campaign_detail', id=id))

@app.route('/admin')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin': return "Akses Ditolak"
    campaigns = []
    if contract:
        count = contract.functions.getCampaignCount().call()
        for i in range(count):
            c = contract.functions.getCampaign(i).call()
            status_map = {0: 'Pending', 1: 'Approved', 2: 'Rejected', 3: 'Deleted'}
            campaigns.append({
                'id': c[0], 'creator_addr': c[1], 'creator_name': get_username_by_wallet(c[1]),
                'title': c[2], 'target': web3.from_wei(c[4], 'ether'),
                'status': status_map[c[8]], 'status_code': c[8]
            })
    conn = get_db_connection(); users = conn.execute('SELECT * FROM users WHERE role != "admin"').fetchall(); conn.close()
    transactions = get_all_transactions()
    return render_template('admin_dashboard.html', campaigns=campaigns, users=users, transactions=transactions)

@app.route('/admin/approve/<int:id>')
def approve_campaign(id):
    try:
        tx = contract.functions.approveCampaign(id).transact({'from': web3.eth.accounts[0]})
        web3.eth.wait_for_transaction_receipt(tx)
    except: pass
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_campaign/<int:id>')
def delete_campaign(id):
    try:
        tx = contract.functions.deleteCampaign(id).transact({'from': web3.eth.accounts[0]})
        web3.eth.wait_for_transaction_receipt(tx)
    except: pass
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    try:
        conn = get_db_connection(); conn.execute('DELETE FROM users WHERE id = ?', (user_id,)); conn.commit(); conn.close()
    except: pass
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('index'))

if __name__ == '__main__': app.run(debug=True, port=5000)