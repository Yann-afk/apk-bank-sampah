from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.auth import role_required
from app.services import PenggunaService, PengepulService, AdminService

# Membuat Blueprint utama untuk aplikasi
main_bp = Blueprint('main', __name__)

# Inisialisasi services
user_service = PenggunaService()
collector_service = PengepulService()
admin_service = AdminService()

# --- Rute Utama dan Dasbor ---

@main_bp.route('/')
def index():
    """
    Halaman utama. Jika sudah login, alihkan ke dasbor.
    Jika belum, alihkan ke halaman login.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Dasbor dinamis berdasarkan peran pengguna.
    """
    # Mengarahkan pengguna ke template dasbor yang sesuai dengan perannya
    if current_user.is_role('pengguna'):
        data = user_service.get_user_dashboard_data(current_user.id)
        return render_template('dashboard_pengguna.html', title="Dasbor Pengguna", data=data)
        
    elif current_user.is_role('pengepul'):
        tasks = collector_service.get_collector_tasks(current_user.id)
        return render_template('dashboard_pengepul.html', title="Dasbor Pengepul", tasks=tasks)
        
    elif current_user.is_role('admin'):
        return render_template('dashboard_admin.html', title="Dasbor Admin")
        
    else:
        # Jika peran tidak dikenali, logout saja
        return redirect(url_for('auth.logout'))

# --- Rute untuk PENGGUNA ---

@main_bp.route('/schedule_pickup', methods=['GET', 'POST'])
@login_required
@role_required('pengguna')
def schedule_pickup():
    """
    Halaman form untuk pengguna menjadwalkan penjemputan.
    """
    if request.method == 'POST':
        tanggal = request.form.get('tanggal')
        waktu = request.form.get('waktu')
        # Ambil alamat dari data pengguna yang login
        lokasi = current_user.data.get('alamat', 'Alamat tidak diatur') 
        notes = request.form.get('notes')
        
        saved_pickup, message = user_service.schedule_pickup(
            current_user.id, tanggal, waktu, lokasi, notes
        )
        
        if saved_pickup:
            flash(message, 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash(message, 'danger')
            
    return render_template('pickup_form.html', title="Jadwalkan Penjemputan")

@main_bp.route('/rewards')
@login_required
@role_required('pengguna')
def reward_catalog():
    """
    Menampilkan katalog reward yang bisa ditukar.
    """
    rewards = user_service.get_rewards_catalog()
    return render_template('reward_catalog.html', title="Katalog Reward", rewards=rewards)

@main_bp.route('/redeem_reward/<string:reward_id>', methods=['POST'])
@login_required
@role_required('pengguna')
def redeem_reward(reward_id):
    """
    Rute untuk memproses permintaan penukaran reward.
    """
    # Hanya izinkan metode POST
    if request.method == 'POST':
        ok, message = user_service.redeem_reward(current_user.id, reward_id)
        
        if ok:
            flash(message, 'success')
        else:
            flash(message, 'danger')
            
    # Kembali ke katalog reward
    return redirect(url_for('main.reward_catalog'))

@main_bp.route('/map')
@login_required
def map_placeholder():
    """
    Halaman placeholder untuk peta bank sampah.
    """
    return render_template('map_placeholder.html', title="Peta Bank Sampah")

# --- Rute untuk PENGEPUL ---

@main_bp.route('/confirm_pickup/<string:pickup_id>', methods=['GET', 'POST'])
@login_required
@role_required('pengepul')
def confirm_pickup(pickup_id):
    """
    Halaman form untuk pengepul mengonfirmasi penjemputan
    dan menginput berat sampah.
    """
    if request.method == 'POST':
        # Mengambil data sampah dari form
        waste_inputs = []
        # Form akan mengirimkan data seperti 'waste_id_wt1' dan 'waste_weight_wt1'
        for key in request.form:
            if key.startswith('waste_weight_'):
                waste_type_id = key.split('waste_weight_')[-1]
                weight = request.form.get(key)
                if weight and float(weight) > 0:
                    waste_inputs.append({
                        "waste_type_id": waste_type_id,
                        "weight": weight
                    })

        if not waste_inputs:
            flash("Anda harus menginput setidaknya satu jenis sampah.", 'warning')
            return redirect(request.url)

        _, message = collector_service.confirm_pickup_and_calculate_points(
            pickup_id, current_user.id, waste_inputs
        )
        
        flash(message, 'success')
        return redirect(url_for('main.dashboard'))

    # Untuk metode GET
    waste_types = collector_service.get_waste_types_for_confirmation()
    return render_template('pickup_confirmation_form.html', # Template baru
                           title="Konfirmasi Setoran",
                           pickup_id=pickup_id,
                           waste_types=waste_types)


# --- Rute untuk ADMIN ---

@main_bp.route('/admin/users')
@login_required
@role_required('admin')
def admin_manage_users():
    """
    Halaman admin untuk mengelola pengguna.
    """
    users = admin_service.get_all_user_accounts()
    return render_template('admin_manage_users.html', title="Manajemen Pengguna", users=users)

@main_bp.route('/admin/master_data', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_manage_master_data():
    """
    Halaman admin untuk mengelola data master (Jenis Sampah & Reward).
    """
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'waste_type':
            nama = request.form.get('waste_nama')
            poin = request.form.get('waste_poin')
            ok, message = admin_service.add_new_waste_type(nama, poin)
        
        elif form_type == 'reward':
            nama = request.form.get('reward_nama')
            deskripsi = request.form.get('reward_deskripsi')
            poin = request.form.get('reward_poin')
            ok, message = admin_service.add_new_reward(nama, deskripsi, poin)
        
        if ok:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('main.admin_manage_master_data'))

    # Untuk metode GET
    data = admin_service.get_master_data()
    return render_template(
        'admin_manage_master_data.html',
        title="Manajemen Data Master",
        waste_types=data['waste_types'],
        rewards=data['rewards']
    )

@main_bp.route('/admin/transactions')
@login_required
@role_required('admin')
def admin_monitor_transactions():
    """
    Halaman admin untuk memonitor semua transaksi.
    """
    transactions = admin_service.get_all_transactions()
    return render_template(
        'admin_monitor_transactions.html',
        title="Monitor Transaksi",
        transactions=transactions
    )

# --- Rute untuk ADMIN (Lanjutan) ---

@main_bp.route('/admin/users/edit/<string:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_edit_user(user_id):
    """
    Rute untuk memproses perubahan data pengguna (Edit).
    """
    nama = request.form.get('nama')
    email = request.form.get('email')
    role = request.form.get('role')
    
    # Memanggil service untuk update data ke database
    # Pastikan AdminService memiliki fungsi update_user_account
    ok, message = admin_service.update_user_account(user_id, nama, email, role)
    
    if ok:
        flash(message, 'success')
    else:
        flash(message, 'danger')
        
    return redirect(url_for('main.admin_manage_users'))

@main_bp.route('/admin/users/delete/<string:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_user(user_id):
    """
    Rute untuk menghapus akun pengguna secara permanen.
    """
    # Memanggil service untuk hapus data dari database
    # Pastikan AdminService memiliki fungsi delete_user_account
    ok, message = admin_service.delete_user_account(user_id)
    
    if ok:
        flash(message, 'success')
    else:
        flash(message, 'danger')
        
    return redirect(url_for('main.admin_manage_users'))