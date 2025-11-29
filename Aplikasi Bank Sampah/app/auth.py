from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
from app.services import AuthService

auth_bp = Blueprint('auth', __name__)

auth_service = AuthService()

class User(UserMixin):
    """
    Kelas User yang kompatibel dengan Flask-Login.
    Ini BUKAN model database, tapi sebuah wrapper untuk data pengguna
    yang diambil dari repository (file JSON).
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

# --- Rute Otentikasi ---

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Menangani proses login pengguna.
    """
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
    """
    Menangani proses registrasi pengguna baru.
    """
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
    """
    Menangani proses logout pengguna.
    """
    logout_user()
    flash('Anda telah berhasil logout.', 'success')
    return redirect(url_for('auth.login'))