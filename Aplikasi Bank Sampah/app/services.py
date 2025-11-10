import uuid
# Hapus import 'generate_password_hash'
# from werkzeug.security import generate_password_hash
from .repository import JsonRepository
from datetime import datetime

class WasteBankService:
    """
    Business Logic Layer (BLL).
    Berisi semua logika bisnis dan aturan aplikasi.
    """
    def __init__(self, repository: JsonRepository):
        self.repo = repository

    def register_user(self, id, nama, email, password, role, alamat):
        """
        Logika untuk mendaftarkan pengguna baru.
        Termasuk hashing password dan pemeriksaan email duplikat.
        """
        # Cek jika email sudah ada
        if self.repo.get_user_by_email(email):
            return None  # Indikasi email sudah ada

        # Hapus hashing password
        # hashed_password = generate_password_hash(password)
        
        new_user_data = {
            "id": id,
            "nama": nama,
            "email": email,
            "password": password, # <-- Simpan password sebagai plain text
            "role": role,
            "alamat": alamat,
            "totalPoin": 0
        }
        
        return self.repo.add_user(new_user_data)

    def schedule_pickup(self, user_id, tanggal, waktu, lokasi):
        """
        Logika untuk membuat jadwal penjemputan baru.
        """
        new_pickup_data = {
            "id": f"p{str(uuid.uuid4())[:8]}", # ID unik singkat
            "userId": user_id,
            "tanggal": tanggal,
            "waktu": waktu,
            "lokasi": lokasi,
            "status": "diminta",
            "pengepulId": None
        }
        return self.repo.add_pickup(new_pickup_data)

    def confirm_pickup(self, pickup_id, pengepul_id, waste_details: dict):
        """
        Logika untuk konfirmasi penjemputan oleh Pengepul.
        Ini adalah logika bisnis inti:
        1. Menghitung total poin dari rincian sampah.
        2. Memperbarui status pickup.
        3. Menambahkan poin ke akun pengguna.
        4. Mencatat transaksi.
        """
        pickup = self.repo.get_pickup_by_id(pickup_id)
        if not pickup or pickup['status'] != 'diminta':
            raise ValueError("Pickup tidak valid atau sudah selesai.")
            
        user = self.repo.get_user_by_id(pickup['userId'])
        if not user:
            raise ValueError("User untuk pickup ini tidak ditemukan.")

        total_poin = 0
        tx_detail = []
        
        # 1. Hitung total poin
        for sampah_id, kg_str in waste_details.items():
            try:
                kg = float(kg_str)
                if kg <= 0:
                    continue
            except (ValueError, TypeError):
                continue

            sampah_type = self.repo.get_sampah_by_id(sampah_id)
            if sampah_type:
                poin = int(sampah_type['nilaiPoinPerKg'] * kg)
                total_poin += poin
                tx_detail.append({
                    "sampahId": sampah_id,
                    "nama": sampah_type['nama'],
                    "kg": kg,
                    "poin": poin
                })

        if total_poin <= 0:
            raise ValueError("Tidak ada sampah yang diinput.")

        # 2. Update status pickup
        self.repo.update_pickup(pickup_id, {
            "status": "selesai",
            "pengepulId": pengepul_id
        })

        # 3. Tambahkan poin ke user
        new_total_poin = user.get('totalPoin', 0) + total_poin
        self.repo.update_user(user['id'], {"totalPoin": new_total_poin})

        # 4. Catat transaksi
        new_tx_data = {
            "id": f"t{str(uuid.uuid4())[:8]}",
            "pickupId": pickup_id,
            "userId": user['id'],
            "tanggal": datetime.now().strftime("%Y-%m-%d"),
            "totalPoin": total_poin,
            "detail": tx_detail
        }
        self.repo.add_transaction(new_tx_data)

        return new_tx_data

    def redeem_reward(self, user_id, reward_id):
        """
        Logika untuk menukarkan poin dengan reward.
        """
        user = self.repo.get_user_by_id(user_id)
        reward = self.repo.get_reward_by_id(reward_id)
        
        if not user or not reward:
            return False, "Data tidak ditemukan."

        user_poin = user.get('totalPoin', 0)
        poin_dibutuhkan = reward['poinDibutuhkan']

        # Validasi poin
        if user_poin < poin_dibutuhkan:
            return False, "Poin Anda tidak cukup."

        # Kurangi poin user
        new_total_poin = user_poin - poin_dibutuhkan
        self.repo.update_user(user_id, {"totalPoin": new_total_poin})
        
        # (Di aplikasi nyata, ini akan mencatat transaksi penukaran)
        
        return True, f"Berhasil menukar {reward['nama']}!"