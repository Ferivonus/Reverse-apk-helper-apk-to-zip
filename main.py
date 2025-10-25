import os
import shutil
import zipfile
from pathlib import Path
import time
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import threading

# Global Değişkenler
ROOT_PATH = None


# --- GÜNCELLENMİŞ DOSYA İŞLEME MANTIĞI ---

def process_folder_recursively(klasor_yolu: Path, extensions: tuple, status_update_func) -> int:
    """
    Belirtilen klasördeki APK'ları ZIP kopyalarına dönüştürür, açar, ZIP'i siler
    ve açılan klasörler için özyinelemeli olarak kendini çağırır.
    """
    if not klasor_yolu.is_dir():
        return 0

    toplam_islenen_dosya = 0
    zip_dosyalari_listesi = []

    # 1. Mevcut klasördeki APK'ların ZIP kopyalarını oluştur
    for dosya_adi in os.listdir(klasor_yolu):
        original_path = klasor_yolu / dosya_adi

        if original_path.is_file() and original_path.suffix.lower() in extensions:

            original_suffix_clean = original_path.suffix.strip('.').lower()

            # Yeni isim formatı: [isim]_[orijinal_uzantı]_old-apk.zip
            new_file_name = f"{original_path.stem}_{original_suffix_clean}_old-apk.zip"
            new_zip_path = original_path.with_name(new_file_name)

            if new_zip_path.exists():
                zip_dosyalari_listesi.append(new_zip_path)
                continue

            try:
                shutil.copy2(original_path, new_zip_path)
                zip_dosyalari_listesi.append(new_zip_path)
                toplam_islenen_dosya += 1

                relative_path = new_zip_path.relative_to(ROOT_PATH)
                status_update_func(f"[Oluşturuldu] -> {relative_path}")

            except Exception as e:
                status_update_func(f"HATA: '{original_path.name}' kopyalanamadı: {e}", is_error=True)

    # 2. Oluşturulan ZIP dosyalarını aç ve 3. ZIP'i sil
    acilan_klasorler = []

    for zip_path in zip_dosyalari_listesi:
        extract_dir_name = zip_path.stem
        extract_dir = zip_path.with_name(extract_dir_name)

        # Klasör daha önce açılmadıysa devam et
        if not extract_dir.exists():
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                acilan_klasorler.append(extract_dir)

                relative_path = zip_path.relative_to(ROOT_PATH)
                status_update_func(f"[Açıldı ve Silindi] -> {relative_path}")

            except Exception as e:
                status_update_func(f"HATA: '{zip_path.name}' açılamadı: {e}", is_error=True)

            finally:
                # ZIP dosyasını açtıktan hemen sonra sil
                try:
                    os.remove(zip_path)
                except Exception as e:
                    status_update_func(f"KRİTİK HATA: '{zip_path.name}' silinemedi! Hata: {e}", is_error=True)

        # Eğer klasör zaten varsa sadece ZIP'i sil
        elif zip_path.exists():
            try:
                os.remove(zip_path)
            except Exception as e:
                status_update_func(f"KRİTİK HATA: '{zip_path.name}' zaten açık klasör varken silinemedi! Hata: {e}",
                                   is_error=True)

    # 4. Yeni açılan her klasör için fonksiyonu tekrar çağır (Özyineleme)
    for new_folder in acilan_klasorler:
        toplam_islenen_dosya += process_folder_recursively(new_folder, extensions, status_update_func)

    return toplam_islenen_dosya


# --- TKINTER ARAYÜZ SINIFI ---

class ApkConverterApp:
    def __init__(self, master):
        self.master = master
        master.title("Özyinelemeli APK Çözme Aracı")
        master.geometry("600x200")
        master.resizable(False, False)

        # Global değişkeni ayarlıyoruz
        global ROOT_PATH
        ROOT_PATH = None
        self.total_conversions = 0

        # 1. Klasör Seçimi
        self.label_path = tk.Label(master, text="İşlem Yapılacak Klasör:")
        self.label_path.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.entry_path = tk.Entry(master, width=60)
        self.entry_path.grid(row=0, column=1, padx=10, pady=10)

        self.button_browse = tk.Button(master, text="Gözat", command=self.browse_folder)
        self.button_browse.grid(row=0, column=2, padx=10, pady=10)

        # 2. İşlem Başlatma Düğmesi
        self.button_start = tk.Button(master, text="İşlemi Başlat", command=self.start_processing_thread, bg="green",
                                      fg="white", state=tk.DISABLED)
        self.button_start.grid(row=1, column=1, pady=10)

        # 3. Durum Çubuğu
        self.status_var = tk.StringVar()
        self.status_var.set("Lütfen bir klasör seçin.")
        self.status_label = tk.Label(master, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=5)

        # Giriş alanındaki değişiklikleri takip et
        self.entry_path.bind("<KeyRelease>", self.check_path_validity)

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, folder_selected)
            self.check_path_validity()

    def check_path_validity(self, event=None):
        path_str = self.entry_path.get().strip()
        is_valid = os.path.isdir(path_str)

        if is_valid:
            self.button_start.config(state=tk.NORMAL)
            self.status_var.set("Klasör hazır. İşlemi başlatabilirsiniz.")
            self.status_label.config(fg="black")
        else:
            self.button_start.config(state=tk.DISABLED)
            if path_str:
                self.status_var.set("HATA: Klasör yolu geçerli değil.")
                self.status_label.config(fg="red")
            else:
                self.status_var.set("Lütfen bir klasör seçin.")
                self.status_label.config(fg="black")

    def update_status(self, message, is_error=False):
        """GUI'daki durumu güncelleyen ve log mesajı gösteren yardımcı fonksiyon."""
        print(message)  # Konsol çıktısı için
        self.status_var.set(message)
        self.status_label.config(fg="red" if is_error else "blue")
        self.master.update_idletasks()  # Arayüzün hemen güncellenmesini zorla

    def start_processing_thread(self):
        """Ana iş parçacığını engellememek için işlemi ayrı bir thread'de başlatır."""
        self.button_start.config(state=tk.DISABLED, text="İşleniyor...")
        self.status_label.config(fg="orange")
        self.update_status("İşlem Başlatıldı. Lütfen Bekleyin...")

        # İşlem mantığını yeni bir thread'e taşı
        processing_thread = threading.Thread(target=self.run_main_process)
        processing_thread.start()

    def run_main_process(self):
        """Dosya işleme mantığını çalıştırır (thread içinde)."""
        global ROOT_PATH
        folder_path_str = self.entry_path.get().strip()

        try:
            klasor_yolu = Path(folder_path_str).resolve()
            ROOT_PATH = klasor_yolu
        except Exception:
            self.update_status(f"HATA: Geçersiz yol: {folder_path_str}", is_error=True)
            self.reset_gui()
            return

        start_time = time.time()

        try:
            # İşleme fonksiyonunu başlat, durum güncelleme callback'ini geçir
            self.total_conversions = process_folder_recursively(
                klasor_yolu,
                extensions=('.apk', '.apkm', '.xapk'),
                status_update_func=self.update_status
            )

            # Başarılı sonlandırma
            end_time = time.time()
            final_message = f"🎉 Başarılı! Toplam {self.total_conversions} dosya çözüldü. Süre: {end_time - start_time:.2f}s"
            self.update_status(final_message)
            messagebox.showinfo("Başarılı", final_message)

        except Exception as e:
            error_message = f"KRİTİK HATA: İşlem sırasında bir sorun oluştu: {e}"
            self.update_status(error_message, is_error=True)
            messagebox.showerror("Hata", error_message)

        self.reset_gui()

    def reset_gui(self):
        """GUI'yı başlangıç durumuna döndürür."""
        self.button_start.config(text="İşlemi Başlat", state=tk.NORMAL)
        self.status_label.config(fg="black")
        self.check_path_validity()  # Klasörün hala geçerli olup olmadığını kontrol et


# --- Ana Çalıştırma ---
if __name__ == "__main__":
    root = tk.Tk()
    app = ApkConverterApp(root)
    root.mainloop()