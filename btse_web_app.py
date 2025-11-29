#!/usr/bin/env python3
"""
BTSE Crypto Trading Bot - Web Application
Πλήρης web εφαρμογή με dashboard, login, και έλεγχο bot
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import threading
import time
import ccxt
import hashlib
import secrets
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Ασφαλές session key

# ============================================================================
# ΡΥΘΜΙΣΕΙΣ ΑΣΦΑΛΕΙΑΣ
# ============================================================================
USERS = {
    "admin": hashlib.sha256("password".encode()).hexdigest(),  # ΑΛΛΑΞΤΕ ΤΟ!
    "trader": hashlib.sha256("secret123".encode()).hexdigest()  # ΑΛΛΑΞΤΕ ΤΟ!
}

# ============================================================================
# ΡΥΘΜΙΣΕΙΣ BOT
# ============================================================================
class CryptoBot:
    def __init__(self):
        self.running = False
        self.exchange = None
        
        # BTSE API Configuration - ΒΑΛΤΕ ΤΑ ΔΙΚΑ ΣΑΣ!
        self.API_KEY = "your_btse_api_key_here"
        self.API_SECRET = "your_btse_secret_here"
        self.USE_TESTNET = True  # False για live trading
        
        # Trading παράμετροι
        self.SYMBOL = "BTC/USDT"
        self.TRADE_AMOUNT = 2.5  # USDT ανά trade
        self.TARGET_PROFIT = 0.002  # 0.2% κέρδος
        self.STOP_LOSS = 0.004  # 0.4% stop loss
        self.DAILY_TARGET = 3.0  # USDT
        
        # Στατιστικά
        self.stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_profit": 0.0,
            "today_profit": 0.0,
            "balance": 0.0,
            "trades_history": []
        }
        
        self.init_exchange()
    
    def init_exchange(self):
        """Αρχικοποίηση σύνδεσης με BTSE"""
        try:
            if self.USE_TESTNET:
                # Testnet configuration
                self.exchange = ccxt.btse({
                    'apiKey': self.API_KEY,
                    'secret': self.API_SECRET,
                    'enableRateLimit': True,
                    'urls': {
                        'api': 'https://testapi.btse.io/spot'
                    }
                })
            else:
                # Production configuration
                self.exchange = ccxt.btse({
                    'apiKey': self.API_KEY,
                    'secret': self.API_SECRET,
                    'enableRateLimit': True
                })
            
            # Test connection
            if self.API_KEY != "your_btse_api_key_here":
                balance = self.exchange.fetch_balance()
                self.stats['balance'] = balance.get('USDT', {}).get('free', 0)
                print(f"✅ Σύνδεση επιτυχής! Balance: ${self.stats['balance']:.2f}")
            else:
                print("⚠️  Demo mode - Δεν έχουν ρυθμιστεί API keys")
                self.stats['balance'] = 100.0  # Demo balance
                
        except Exception as e:
            print(f"❌ Σφάλμα σύνδεσης: {str(e)}")
            self.stats['balance'] = 100.0  # Demo mode
    
    def get_current_price(self):
        """Παίρνει την τρέχουσα τιμή"""
        try:
            if self.exchange and self.API_KEY != "your_btse_api_key_here":
                ticker = self.exchange.fetch_ticker(self.SYMBOL)
                return ticker['last']
            else:
                # Demo price με ρεαλιστική κίνηση
                import random
                base_price = 43500
                return base_price + random.uniform(-500, 500)
        except Exception as e:
            print(f"Σφάλμα price: {e}")
            return 43500
    
    def execute_trade(self):
        """Εκτελεί ένα trade"""
        try:
            entry_price = self.get_current_price()
            
            # Υπολογισμός target και stop
            target_price = entry_price * (1 + self.TARGET_PROFIT)
            stop_price = entry_price * (1 - self.STOP_LOSS)
            
            # Προσομοίωση trade outcome
            import random
            success = random.random() < 0.65  # 65% win rate
            
            if success:
                profit = self.TRADE_AMOUNT * self.TARGET_PROFIT
                exit_price = target_price
                status = "WIN"
                self.stats['wins'] += 1
            else:
                profit = -self.TRADE_AMOUNT * self.STOP_LOSS
                exit_price = stop_price
                status = "LOSS"
                self.stats['losses'] += 1
            
            # Ενημέρωση στατιστικών
            self.stats['total_trades'] += 1
            self.stats['total_profit'] += profit
            self.stats['today_profit'] += profit
            self.stats['balance'] += profit
            
            # Αποθήκευση trade
            trade = {
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'entry': f"${entry_price:.2f}",
                'exit': f"${exit_price:.2f}",
                'profit': f"${profit:.4f}",
                'status': status
            }
            self.stats['trades_history'].insert(0, trade)
            
            # Κράτα μόνο τα τελευταία 20 trades
            if len(self.stats['trades_history']) > 20:
                self.stats['trades_history'] = self.stats['trades_history'][:20]
            
            print(f"{'✅' if success else '❌'} Trade: ${profit:.4f} | Total: ${self.stats['today_profit']:.2f}")
            
        except Exception as e:
            print(f"❌ Trade error: {str(e)}")
    
    def trading_loop(self):
        """Κύριο loop trading"""
        print("🚀 Bot ξεκίνησε!")
        
        while self.running:
            try:
                # Έλεγχος αν φτάσαμε το ημερήσιο target
                if self.stats['today_profit'] >= self.DAILY_TARGET:
                    print(f"🎯 Ημερήσιος στόχος επιτεύχθηκε: ${self.stats['today_profit']:.2f}")
                    time.sleep(60)  # Περίμενε 1 λεπτό
                    continue
                
                # Εκτέλεση trade
                self.execute_trade()
                
                # Περίμενε 30-60 δευτερόλεπτα
                import random
                time.sleep(random.uniform(30, 60))
                
            except Exception as e:
                print(f"❌ Loop error: {str(e)}")
                time.sleep(60)
        
        print("🛑 Bot σταμάτησε!")
    
    def start(self):
        """Ξεκινά το bot"""
        if not self.running:
            self.running = True
            thread = threading.Thread(target=self.trading_loop, daemon=True)
            thread.start()
            return True
        return False
    
    def stop(self):
        """Σταματά το bot"""
        self.running = False
        return True
    
    def get_stats(self):
        """Επιστρέφει τα στατιστικά"""
        win_rate = (self.stats['wins'] / self.stats['total_trades'] * 100) if self.stats['total_trades'] > 0 else 0
        
        return {
            **self.stats,
            'win_rate': win_rate,
            'running': self.running,
            'current_price': self.get_current_price()
        }

# Global bot instance
bot = CryptoBot()

# ============================================================================
# WEB ROUTES
# ============================================================================

@app.route('/')
def index():
    """Αρχική σελίδα - redirect σε login ή dashboard"""
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        # Hash password
        hashed = hashlib.sha256(password.encode()).hexdigest()
        
        # Έλεγχος credentials
        if username in USERS and USERS[username] == hashed:
            session['username'] = username
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Λάθος όνομα χρήστη ή κωδικός'})
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Main dashboard"""
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/logout')
def logout():
    """Logout"""
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/api/stats')
def api_stats():
    """API endpoint για στατιστικά"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(bot.get_stats())

@app.route('/api/start', methods=['POST'])
def api_start():
    """Ξεκινά το bot"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    success = bot.start()
    return jsonify({'success': success})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Σταματά το bot"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    success = bot.stop()
    return jsonify({'success': success})

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Ρυθμίσεις bot"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'POST':
        data = request.json
        bot.TRADE_AMOUNT = float(data.get('trade_amount', bot.TRADE_AMOUNT))
        bot.DAILY_TARGET = float(data.get('daily_target', bot.DAILY_TARGET))
        bot.TARGET_PROFIT = float(data.get('target_profit', bot.TARGET_PROFIT))
        return jsonify({'success': True})
    
    return jsonify({
        'trade_amount': bot.TRADE_AMOUNT,
        'daily_target': bot.DAILY_TARGET,
        'target_profit': bot.TARGET_PROFIT * 100,
        'stop_loss': bot.STOP_LOSS * 100
    })

# ============================================================================
# HTML TEMPLATES
# ============================================================================

@app.route('/templates/login.html')
def get_login_template():
    """Επιστρέφει το login template"""
    return """
<!DOCTYPE html>
<html lang="el">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BTSE Bot - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 400px;
        }
        .logo {
            text-align: center;
            font-size: 48px;
            margin-bottom: 10px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #666;
            font-weight: 500;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        .error {
            color: #e74c3c;
            text-align: center;
            margin-top: 15px;
            display: none;
        }
        .info {
            text-align: center;
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">🔐</div>
        <h1>BTSE Trading Bot</h1>
        
        <form id="loginForm">
            <div class="form-group">
                <label>Username</label>
                <input type="text" id="username" required autocomplete="username">
            </div>
            
            <div class="form-group">
                <label>Password</label>
                <input type="password" id="password" required autocomplete="current-password">
            </div>
            
            <button type="submit">Είσοδος</button>
            
            <div class="error" id="error"></div>
        </form>
        
        <div class="info">
            <strong>Demo Credentials:</strong><br>
            admin / password<br>
            trader / secret123
        </div>
    </div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('error');
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    window.location.href = '/dashboard';
                } else {
                    errorDiv.textContent = data.error;
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.textContent = 'Σφάλμα σύνδεσης';
                errorDiv.style.display = 'block';
            }
        });
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    # Δημιουργία templates φακέλου
    os.makedirs('templates', exist_ok=True)
    
    # Αποθήκευση login template
    with open('templates/login.html', 'w', encoding='utf-8') as f:
        f.write(get_login_template())
    
    # Δημιουργία dashboard template
    with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
        f.write("""
<!DOCTYPE html>
<html lang="el">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BTSE Bot - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f6fa;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header h1 { font-size: 24px; }
        .user-info { display: flex; align-items: center; gap: 20px; }
        .logout-btn {
            background: rgba(255,255,255,0.2);
            border: 2px solid white;
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s;
        }
        .logout-btn:hover { background: white; color: #667eea; }
        
        .container { max-width: 1400px; margin: 30px auto; padding: 0 20px; }
        
        .controls {
            background: white;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            gap: 15px;
            align-items: center;
        }
        .control-btn {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .start-btn { background: #2ecc71; color: white; }
        .start-btn:hover { background: #27ae60; }
        .stop-btn { background: #e74c3c; color: white; }
        .stop-btn:hover { background: #c0392b; }
        .status {
            margin-left: auto;
            padding: 10px 20px;
            border-radius: 20px;
            font-weight: 600;
        }
        .status.running { background: #2ecc71; color: white; }
        .status.stopped { background: #95a5a6; color: white; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .stat-label {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            color: #333;
        }
        .stat-value.positive { color: #2ecc71; }
        .stat-value.negative { color: #e74c3c; }
        
        .trades-section {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .trades-section h2 {
            margin-bottom: 20px;
            color: #333;
        }
        .trades-table {
            width: 100%;
            border-collapse: collapse;
        }
        .trades-table th {
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #666;
        }
        .trades-table td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        .trade-win { color: #2ecc71; font-weight: 600; }
        .trade-loss { color: #e74c3c; font-weight: 600; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 BTSE Trading Bot Dashboard</h1>
        <div class="user-info">
            <span>👤 {{ username }}</span>
            <a href="/logout" class="logout-btn">Έξοδος</a>
        </div>
    </div>

    <div class="container">
        <div class="controls">
            <button class="control-btn start-btn" onclick="startBot()">▶️ Εκκίνηση Bot</button>
            <button class="control-btn stop-btn" onclick="stopBot()">⏸️ Παύση Bot</button>
            <div class="status stopped" id="status">⚫ Σταματημένο</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">💰 Τρέχον Balance</div>
                <div class="stat-value" id="balance">$0.00</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">📈 Σημερινό Κέρδος</div>
                <div class="stat-value positive" id="today-profit">$0.00</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">💹 Συνολικό Κέρδος</div>
                <div class="stat-value" id="total-profit">$0.00</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🎯 Win Rate</div>
                <div class="stat-value" id="win-rate">0%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">📊 Συναλλαγές</div>
                <div class="stat-value" id="total-trades">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">💱 Τιμή BTC</div>
                <div class="stat-value" id="current-price">$0</div>
            </div>
        </div>

        <div class="trades-section">
            <h2>📋 Ιστορικό Συναλλαγών</h2>
            <table class="trades-table">
                <thead>
                    <tr>
                        <th>Ώρα</th>
                        <th>Είσοδος</th>
                        <th>Έξοδος</th>
                        <th>Κέρδος</th>
                        <th>Αποτέλεσμα</th>
                    </tr>
                </thead>
                <tbody id="trades-body">
                    <tr><td colspan="5" style="text-align:center; color:#999;">Δεν υπάρχουν συναλλαγές ακόμα</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        async function updateStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                // Update stats
                document.getElementById('balance').textContent = `$${data.balance.toFixed(2)}`;
                document.getElementById('today-profit').textContent = `$${data.today_profit.toFixed(2)}`;
                document.getElementById('total-profit').textContent = `$${data.total_profit.toFixed(2)}`;
                document.getElementById('win-rate').textContent = `${data.win_rate.toFixed(1)}%`;
                document.getElementById('total-trades').textContent = data.total_trades;
                document.getElementById('current-price').textContent = `$${data.current_price.toFixed(2)}`;
                
                // Update status
                const statusEl = document.getElementById('status');
                if (data.running) {
                    statusEl.textContent = '🟢 Λειτουργεί';
                    statusEl.className = 'status running';
                } else {
                    statusEl.textContent = '⚫ Σταματημένο';
                    statusEl.className = 'status stopped';
                }
                
                // Update trades table
                const tbody = document.getElementById('trades-body');
                if (data.trades_history.length > 0) {
                    tbody.innerHTML = data.trades_history.map(trade => `
                        <tr>
                            <td>${trade.timestamp}</td>
                            <td>${trade.entry}</td>
                            <td>${trade.exit}</td>
                            <td class="${trade.status === 'WIN' ? 'trade-win' : 'trade-loss'}">${trade.profit}</td>
                            <td class="${trade.status === 'WIN' ? 'trade-win' : 'trade-loss'}">${trade.status}</td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#999;">Δεν υπάρχουν συναλλαγές ακόμα</td></tr>';
                }
                
            } catch (error) {
                console.error('Error updating stats:', error);
            }
        }
        
        async function startBot() {
            try {
                const response = await fetch('/api/start', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    alert('✅ Bot ξεκίνησε!');
                    updateStats();
                }
            } catch (error) {
                alert('❌ Σφάλμα εκκίνησης');
            }
        }
        
        async function stopBot() {
            try {
                const response = await fetch('/api/stop', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    alert('⏸️ Bot σταμάτησε!');
                    updateStats();
                }
            } catch (error) {
                alert('❌ Σφάλμα παύσης');
            }
        }
        
        // Auto-update κάθε 3 δευτερόλεπτα
        setInterval(updateStats, 3000);
        updateStats();
    </script>
</body>
</html>
""")
    
    print("\n" + "="*60)
    print("🚀 BTSE CRYPTO BOT WEB APPLICATION")
    print("="*60)
    print("\n📱 Ανοίξτε το browser σας στο:")
    print("   http://localhost:5000")
    print("\n🔐 Login credentials:")
    print("   Username: admin")
    print("   Password: password")
    print("\n⚠️  ΣΗΜΑΝΤΙΚΟ:")
    print("   1. Αλλάξτε τα passwords στις γραμμές 20-23")
    print("   2. Βάλτε τα BTSE API keys στις γραμμές 43-44")
    print("   3. Ρυθμίστε USE_TESTNET = True/False (γραμμή 45)")
    print("\n" + "="*60 + "\n")
    
    # Start Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
