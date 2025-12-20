import os
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename
from app.repository import UserRepository, DataRepository

# Inisialisasi repositori
user_repo = UserRepository()
data_repo = DataRepository()

class AuthService:
    """
    Service untuk menangani logika terkait otentikasi.
    """
    def register_user(self, nama, email, password, role, alamat, area_tugas=None):
        """
        Mendaftarkan pengguna baru.
        """
        # Cek apakah email sudah ada
        if user_repo.get_user_by_email(email):
            return None, "Email sudah terdaftar."
        
        # Menyimpan password sebagai plain text (Sesuai permintaan khusus)
        password_plain = password

        # Siapkan data pengguna baru
        new_user_data = {
            "id": None, # Akan di-generate oleh repository
            "nama": nama,
            "email": email,
            "password": password_plain,
            "role": role,
            "total_poin": 0,
            "alamat": alamat,
            "area_tugas": area_tugas if role == 'pengepul' else None,
            "is_shadow_banned": False, # Default: Tidak kena ban
            "needs_extra_verification": False, # Default: Tidak butuh verifikasi foto
            "ban_until": None # Tanggal berakhir ban
        }

        # Simpan pengguna baru
        try:
            saved_user = user_repo.save_user(new_user_data)
            return saved_user, "Registrasi berhasil."
        except Exception as e:
            return None, f"Terjadi kesalahan saat registrasi: {e}"

    def authenticate_user(self, email, password):
        """
        Mengotentikasi pengguna untuk login.
        """
        user_data = user_repo.get_user_by_email(email)
        
        if not user_data:
            return None, "Email tidak ditemukan."
            
        if user_data.get('password') != password:
            return None, "Password salah."
            
        return user_data, "Login berhasil."

class PenggunaService:
    """
    Service untuk logika bisnis yang terkait dengan Pengguna.
    """
    def schedule_pickup(self, user_id, tanggal, waktu, lokasi, notes, waste_photo=None):
        """
        Membuat jadwal penjemputan baru.
        Mendukung verifikasi tambahan melalui waste_photo.
        """
        # Logika Tambahan: Jika foto wajib (needs_extra_verification) tapi tidak ada
        user = user_repo.get_user_by_id(user_id)
        if user.get('needs_extra_verification') and not waste_photo:
            return None, "Anda wajib mengunggah foto sampah untuk verifikasi."

        filename = None
        # --- LOGIKA PENYIMPANAN FILE FISIK ---
        if waste_photo and waste_photo.filename != '':
            # 1. Amankan nama file dengan timestamp agar unik
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = secure_filename(f"{timestamp}_{waste_photo.filename}")
            
            # 2. Tentukan path folder static/uploads/waste_photos
            upload_path = os.path.join(current_app.root_path, 'static', 'uploads', 'waste_photos')
            
            # 3. Buat folder jika belum ada
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            
            # 4. Simpan file secara fisik ke server
            try:
                waste_photo.save(os.path.join(upload_path, filename))
            except Exception as e:
                return None, f"Gagal menyimpan file foto: {e}"

        pickup_data = {
            "user_id": user_id,
            "tanggal": tanggal,
            "waktu": waktu,
            "lokasi": lokasi,
            "status": "menunggu",
            "pengepul_id": None,
            "notes": notes,
            "photo_path": filename # Menyimpan nama file hasil proses ke database
        }
        
        try:
            saved_pickup = data_repo.save_pickup(pickup_data)
            return saved_pickup, "Jadwal berhasil dibuat."
        except Exception as e:
            return None, f"Gagal membuat jadwal: {e}"
            
    def get_user_dashboard_data(self, user_id):
        """
        Mengambil data untuk dasbor pengguna.
        """
        user_data = user_repo.get_user_by_id(user_id)
        pickups = data_repo.get_pickups_by_user_id(user_id)
        pickups.sort(key=lambda x: x.get('tanggal'), reverse=True)
        
        return {
            "user": user_data,
            "recent_pickups": pickups[:5]
        }

    def get_rewards_catalog(self):
        """
        Mengambil daftar reward yang tersedia.
        """
        return data_repo.get_all_rewards()

    def redeem_reward(self, user_id, reward_id):
        """
        Logika inti: Menukarkan poin dengan reward.
        """
        user = user_repo.get_user_by_id(user_id)
        reward = data_repo.get_reward_by_id(reward_id)

        if not user:
            return False, "Pengguna tidak ditemukan."
        if not reward:
            return False, "Reward tidak ditemukan."

        poin_dibutuhkan = reward.get('poin_dibutuhkan', 0)
        poin_pengguna = user.get('total_poin', 0)

        if poin_pengguna < poin_dibutuhkan:
            return False, "Poin Anda tidak cukup untuk menukar reward ini."
            
        user['total_poin'] = poin_pengguna - poin_dibutuhkan
        
        transaction_data = {
            "user_id": user['id'],
            "tanggal": datetime.now().strftime('%Y-%m-%d'),
            "tipe": "redeem_reward",
            "deskripsi": f"Tukar: {reward.get('nama')}",
            "jumlah_poin": -poin_dibutuhkan
        }
        
        try:
            data_repo.redeem_reward_transaction(user, transaction_data)
            return True, f"Reward '{reward.get('nama')}' berhasil ditukar!"
        except Exception as e:
            return False, f"Gagal menyimpan transaksi redeem: {e}"

class PengepulService:
    """
    Service untuk logika bisnis yang terkait dengan Pengepul.
    """
    def get_collector_tasks(self, collector_id):
        """
        Mengambil daftar tugas untuk pengepul.
        """
        all_tasks = data_repo.get_pickups_by_collector_id(collector_id)
        tasks = [
            task for task in all_tasks 
            if task['status'] == 'menunggu' or task.get('pengepul_id') == collector_id
        ]
        tasks.sort(key=lambda x: (x.get('tanggal'), x.get('waktu')))
        return tasks

    def get_waste_types_for_confirmation(self):
        """
        Mengambil jenis sampah untuk ditampilkan di form konfirmasi.
        """
        return data_repo.get_all_waste_types()

    def confirm_pickup_and_calculate_points(self, pickup_id, collector_id, waste_inputs):
        """
        Logika inti: Konfirmasi penjemputan dan hitung poin.
        """
        pickup = data_repo.get_pickup_by_id(pickup_id)
        if not pickup:
            return None, "Jadwal penjemputan tidak ditemukan."
            
        if pickup['status'] == 'selesai':
            return None, "Penjemputan ini sudah diselesaikan."

        user = user_repo.get_user_by_id(pickup['user_id'])
        if not user:
            return None, "Data pengguna tidak ditemukan."

        all_waste_types = data_repo.get_all_waste_types()
        waste_map = {wt['id']: wt for wt in all_waste_types}

        total_poin = 0
        deskripsi_transaksi = "Setor sampah ("
        
        for item in waste_inputs:
            waste_type_id = item.get('waste_type_id')
            try:
                weight = float(item.get('weight', 0))
            except (ValueError, TypeError):
                weight = 0.0

            if waste_type_id in waste_map and weight > 0:
                waste_type = waste_map[waste_type_id]
                poin = weight * waste_type['nilai_poin_per_kg']
                total_poin += poin
                deskripsi_transaksi += f"{waste_type['nama']}: {weight}kg, "
        
        deskripsi_transaksi = deskripsi_transaksi.rstrip(', ') + ")"
        
        if total_poin == 0:
            return None, "Tidak ada sampah yang diinput. Poin tidak ditambahkan."

        pickup['status'] = 'selesai'
        pickup['pengepul_id'] = collector_id
        user['total_poin'] = user.get('total_poin', 0) + total_poin
        
        transaction_data = {
            "user_id": user['id'],
            "tanggal": datetime.now().strftime('%Y-%m-%d'),
            "tipe": "setor_sampah",
            "deskripsi": deskripsi_transaksi,
            "jumlah_poin": total_poin
        }
        
        try:
            data_repo.confirm_pickup_transaction(pickup, transaction_data, user)
            return pickup, f"Konfirmasi berhasil. {total_poin} poin ditambahkan ke pengguna."
        except Exception as e:
            return None, f"Gagal menyimpan konfirmasi: {e}"

    def report_pickup_violation(self, pickup_id):
        """
        Logika untuk menangani laporan pelanggaran (misal: sampah tidak ada di lokasi).
        """
        pickup = data_repo.get_pickup_by_id(pickup_id)
        if not pickup:
            return False, "Jadwal penjemputan tidak ditemukan."

        if pickup['status'] != 'menunggu':
            return False, "Tugas ini sudah diproses sebelumnya."

        # 1. Ubah status penjemputan menjadi 'pelanggaran'
        pickup['status'] = 'pelanggaran'
        
        # 2. Ambil data user untuk memberikan sanksi
        user = user_repo.get_user_by_id(pickup['user_id'])
        if user:
            # Sanksi: Tugas berikutnya wajib unggah foto
            user['needs_extra_verification'] = True
            
            try:
                # Simpan perubahan ke repository
                user_repo.update_user(user['id'], user)
                # Gunakan fungsi update yang ada di repository Anda
                data_repo.update_pickup(pickup_id, pickup) 
                return True, f"Laporan terkirim. {user['nama']} kini wajib verifikasi foto untuk tugas selanjutnya."
            except Exception as e:
                return False, f"Terjadi kesalahan database: {e}"
        
        return False, "User terkait tidak ditemukan."

class AdminService:
    """
    Service untuk logika bisnis yang terkait dengan Admin.
    """
    def get_all_user_accounts(self):
        """Mengambil semua akun pengguna."""
        return user_repo.get_all_users()

    def update_user_account(self, user_id, nama, email, role):
        """Memperbarui data akun pengguna."""
        try:
            user = user_repo.get_user_by_id(user_id)
            if not user:
                return False, "Pengguna tidak ditemukan."
            
            user['nama'] = nama
            user['email'] = email
            user['role'] = role
            
            # Pastikan UserRepository memiliki fungsi update_user
            success = user_repo.update_user(user_id, user) 
            if success:
                return True, f"Data pengguna {nama} berhasil diperbarui."
            return False, "Gagal mengupdate data di database."
        except Exception as e:
            return False, f"Gagal memperbarui data: {e}"

    def delete_user_account(self, user_id):
        """Menghapus akun pengguna."""
        try:
            # Pastikan UserRepository memiliki fungsi delete_user
            success = user_repo.delete_user(user_id)
            if success:
                return True, "Pengguna berhasil dihapus."
            return False, "Pengguna tidak ditemukan atau gagal dihapus."
        except Exception as e:
            return False, f"Gagal menghapus pengguna: {e}"
        
    def get_master_data(self):
        """Mengambil data master."""
        return {
            "waste_types": data_repo.get_all_waste_types(),
            "rewards": data_repo.get_all_rewards()
        }
        
    def get_all_transactions(self):
        """Mengambil semua riwayat transaksi."""
        transactions = data_repo.get_all_transactions()
        users_map = {u['id']: u for u in user_repo.get_all_users()}
        
        for t in transactions:
            t['user_nama'] = users_map.get(t['user_id'], {}).get('nama', 'N/A')
            
        transactions.sort(key=lambda x: x.get('tanggal'), reverse=True)
        return transactions

    def add_new_waste_type(self, nama, nilai_poin_per_kg):
        try:
            waste_data = {
                "nama": nama,
                "nilai_poin_per_kg": int(nilai_poin_per_kg)
            }
            data_repo.save_waste_type(waste_data)
            return True, "Jenis sampah baru berhasil ditambahkan."
        except Exception as e:
            return False, f"Gagal menambahkan: {e}"

    def add_new_reward(self, nama, deskripsi, poin_dibutuhkan):
        try:
            reward_data = {
                "nama": nama,
                "deskripsi": deskripsi,
                "poin_dibutuhkan": int(poin_dibutuhkan)
            }
            data_repo.save_reward(reward_data)
            return True, "Reward baru berhasil ditambahkan."
        except Exception as e:
            return False, f"Gagal menambahkan: {e}"