from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps

# --- Tambahan untuk Google OAuth (Flask-Dance) ---
from flask_dance.contrib.google import make_google_blueprint, google
from requests.exceptions import ConnectionError, HTTPError
import os
# --- Akhir Tambahan ---

from app.services import AuthService

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

# ====================================================================
# 1. KONFIGURASI GOOGLE OAUTH
# ====================================================================

# PENTING: Ganti nilai-nilai ini dengan environment variables yang sebenarnya 
# di aplikasi produksi Anda.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_CLIENT_ID_HERE")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "YOUR_CLIENT_SECRET_HERE")

# Buat Google Blueprint
google_bp = make_google_blueprint(
    client_id=GOOGLE_CLIENT_ID, 
    client_secret=GOOGLE_CLIENT_SECRET,
    scope=["profile", "email"],
    # Endpoint ini akan dipanggil setelah pertukaran token sukses oleh Flask-Dance
    redirect_to="auth.google_authorized_handler" 
)

# ====================================================================
# 2. DEFINISI KELAS DAN DECORATOR
# ====================================================================

class User(UserMixin):
    """
    Kelas User yang kompatibel dengan Flask-Login.
    """
    def __init__(self, user_data):
        self.id = user_data.get('id')
        self.nama = user_data.get('nama')
        self.email = user_data.get('email')
        self.role = user_data.get('role')
        self.data = user_data # Menyimpan semua data asli

    def get_id(self):
        """Mengembalikan ID pengguna (harus string)."""
        return str(self.id)

    def is_role(self, role_name):
        """Memeriksa apakah pengguna memiliki peran tertentu."""
        return self.role == role_name

# --- Decorator Kustom untuk Cek Peran ---

def role_required(role_name):
    """
    Decorator untuk membatasi akses route berdasarkan peran pengguna.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Cek apakah pengguna sudah login
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            
            # Cek apakah pengguna memiliki peran yang diizinkan
            if not current_user.is_role(role_name):
                flash(f"Akses ditolak. Halaman ini khusus untuk {role_name}.", 'danger')
                return redirect(url_for('main.index')) # Alihkan ke halaman utama
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ====================================================================
# 3. RUTE OTENTIKASI EMAIL/PASSWORD
# ====================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Menangani proses login pengguna."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_data, message = auth_service.authenticate_user(email, password)
        
        if user_data:
            user_obj = User(user_data)
            login_user(user_obj, remember=request.form.get('remember'))
            flash(message, 'success')

            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash(message, 'danger')
            
    return render_template('login.html', title="Login")

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Menangani proses registrasi pengguna baru."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        nama = request.form.get('nama')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'pengguna') # Default 'pengguna'
        alamat = request.form.get('alamat')
        area_tugas = request.form.get('area_tugas')

        if password != request.form.get('confirm_password'):
            flash("Password dan konfirmasi password tidak cocok.", 'danger')
            return render_template('register.html', title="Register")

        saved_user, message = auth_service.register_user(
            nama, email, password, role, alamat, area_tugas
        )
        
        if saved_user:
            flash(message, 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'danger')
            
    return render_template('register.html', title="Register")

@auth_bp.route('/logout')
@login_required
def logout():
    """Menangani proses logout pengguna."""
    logout_user()
    flash('Anda telah berhasil logout.', 'success')
    return redirect(url_for('auth.login'))

# ====================================================================
# 4. RUTE OTENTIKASI GOOGLE (OAUTH 2.0)
# ====================================================================

@auth_bp.route('/google_login')
def google_login():
    """
    Langkah 1: Memulai proses OAuth dengan mengarahkan pengguna ke Google.
    Route ini dipanggil dari tombol 'Masuk dengan Google' di login.html.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Jika pengguna belum terotorisasi, Flask-Dance akan mengarahkan
    # mereka ke halaman login Google.
    if not google.authorized:
        # Nama 'google.login' berasal dari Flask-Dance, 
        # di mana 'google' adalah nama blueprint.
        return redirect(url_for("google.login")) 
    
    # Jika sudah terotorisasi (misalnya sesi masih ada), langsung proses
    return redirect(url_for('auth.google_authorized_handler'))


@auth_bp.route('/google_authorized_handler')
def google_authorized_handler():
    """
    Langkah 2: Menangani respons (callback) dari Google setelah otorisasi.
    Ini adalah fungsi yang didefinisikan di parameter `redirect_to` pada `make_google_blueprint`.
    """
    # Cek apakah Flask-Dance berhasil mendapatkan token dari Google
    if not google.authorized:
        flash("Gagal masuk dengan Google. Pastikan akses diberikan.", 'danger')
        return redirect(url_for("auth.login"))

    try:
        # Dapatkan data user (email, nama, dll.) dari Google API
        resp = google.get("/oauth2/v2/userinfo")
        
        if not resp.ok:
            flash("Gagal mendapatkan informasi pengguna dari Google.", 'danger')
            return redirect(url_for("auth.login"))
            
        google_user_data = resp.json()
        email = google_user_data.get("email")
        nama = google_user_data.get("name")
        
        # --- LOGIKA OTENTIKASI/PENDAFTARAN MENGGUNAKAN EMAIL GOOGLE ---
        
        # 1. Cari pengguna di database Anda berdasarkan email Google
        user_data = auth_service.get_user_by_email(email)

        if user_data:
            # Jika user sudah terdaftar, login
            user_obj = User(user_data)
            login_user(user_obj)
            flash(f'Selamat datang kembali, {user_obj.nama}!', 'success')
        else:
            # Jika user belum terdaftar, daftarkan otomatis (tanpa password)
            # Karena ini adalah pendaftaran dari pihak ketiga (Google), 
            # kita asumsikan user adalah 'pengguna' dan tidak perlu password.
            # Anda perlu menyesuaikan AuthService.register_user untuk mendukung 
            # pendaftaran tanpa password atau membuat method baru.
            
            # Implementasi sementara: Daftarkan sebagai pengguna baru
            # CATATAN: Pastikan AuthService.register_user bisa menangani
            # pendaftaran dari Google (tanpa password, dll.)
            new_user_data, message = auth_service.register_user_google(
                 nama=nama, 
                 email=email, 
                 role='pengguna'
            )
            
            if new_user_data:
                 user_obj = User(new_user_data)
                 login_user(user_obj)
                 flash('Pendaftaran via Google berhasil. Selamat datang!', 'success')
            else:
                 flash(f'Pendaftaran via Google gagal: {message}', 'danger')
                 return redirect(url_for('auth.login'))
                 
        # --- AKHIR LOGIKA OTENTIKASI ---
        
        return redirect(url_for("main.dashboard"))

    except (ConnectionError, HTTPError, Exception) as e:
        flash(f"Terjadi kesalahan saat otentikasi Google: {e}", 'danger')
        return redirect(url_for("auth.login"))
        
# Catatan: Rute placeholder lama (/google_callback) telah dihapus/diganti
# dengan google_authorized_handler yang lebih fungsional.