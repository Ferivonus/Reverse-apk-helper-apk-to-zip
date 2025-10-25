import os
import shutil
import zipfile
from pathlib import Path
import time
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import threading

# Global Değişkenler
ROOT_PATH = None


# --- DOSYA İŞLEME MANTIĞI (Önceki Koddan Devam) ---

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
                status_update_func(f"[Oluşturuldu] -> {relative_path}", log_only=True)

            except Exception as e:
                status_update_func(f"HATA: '{original_path.name}' kopyalanamadı: {e}", is_error=True)

    # 2. Oluşturulan ZIP dosyalarını aç ve 3. ZIP'i sil
    acilan_klasorler = []

    for zip_path in zip_dosyalari_listesi:
        extract_dir_name = zip_path.stem
        extract_dir = zip_path.with_name(extract_dir_name)

        if not extract_dir.exists():
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                acilan_klasorler.append(extract_dir)

                relative_path = zip_path.relative_to(ROOT_PATH)
                status_update_func(f"[Açıldı ve Silindi] -> {relative_path}", log_only=True)

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
        master.title("Özyinelemeli APK Çözme Aracı (v2.0)")
        master.geometry("700x550")

        self.total_conversions = 0
        global ROOT_PATH
        ROOT_PATH = None

        # Ana konteyner (frame)
        self.main_frame = ttk.Frame(master, padding="10 10 10 10")
        self.main_frame.pack(fill='both', expand=True)

        # 1. Giriş/Kontrol Çerçevesi
        self.control_frame = ttk.LabelFrame(self.main_frame, text="Kontrol Paneli", padding="10")
        self.control_frame.grid(row=0, column=0, sticky="ew", pady=10)
        self.control_frame.grid_columnconfigure(1, weight=1)  # Giriş alanının genişlemesini sağla

        # Klasör Seçimi
        ttk.Label(self.control_frame, text="Klasör Yolu:", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5,
                                                                                            pady=5, sticky="w")

        self.entry_path = ttk.Entry(self.control_frame, width=70)
        self.entry_path.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.button_browse = ttk.Button(self.control_frame, text="Gözat", command=self.browse_folder)
        self.button_browse.grid(row=0, column=2, padx=5, pady=5)

        # İşlem Başlatma Düğmesi
        self.button_start = ttk.Button(self.control_frame, text="İşlemi BAŞLAT", command=self.start_processing_thread,
                                       state=tk.DISABLED, style='Accent.TButton')
        self.button_start.grid(row=1, column=1, pady=10, sticky="ew")

        # 2. Durum ve İlerleme Çerçevesi
        self.status_frame = ttk.Frame(self.main_frame, padding="5")
        self.status_frame.grid(row=1, column=0, sticky="ew", pady=5)
        self.status_frame.grid_columnconfigure(0, weight=1)

        # İlerleme Çubuğu
        self.progress_bar = ttk.Progressbar(self.status_frame, orient='horizontal', mode='indeterminate', length=650)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=5)

        # Genel Durum Etiketi
        self.status_var = tk.StringVar()
        self.status_var.set("Lütfen bir klasör seçin.")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var, font=('Arial', 10, 'italic'),
                                      anchor=tk.W)
        self.status_label.grid(row=1, column=0, sticky="ew")

        # 3. Log Çerçevesi
        self.log_frame = ttk.LabelFrame(self.main_frame, text="İşlem Logları", padding="10")
        self.log_frame.grid(row=2, column=0, sticky="nsew", pady=10)
        self.main_frame.grid_rowconfigure(2, weight=1)  # Log alanının dikeyde genişlemesini sağla
        self.log_frame.grid_columnconfigure(0, weight=1)

        # Log Text Alanı (Kaydırılabilir)
        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, width=80, height=15,
                                                  font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.config(state=tk.DISABLED)  # Salt okunur yap

        # Tkinter stilini ayarla (isteğe bağlı, daha düzgün görünüm için)
        s = ttk.Style()
        s.theme_use('clam')  # 'clam' veya 'alt' modern temalardır
        s.configure('Accent.TButton', foreground='white', background='#0078D4')

        # Giriş alanındaki değişiklikleri takip et
        self.entry_path.bind("<KeyRelease>", self.check_path_validity)

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, folder_selected)
            self.check_path_validity()
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete('1.0', tk.END)
            self.log_text.config(state=tk.DISABLED)

    def check_path_validity(self, event=None):
        path_str = self.entry_path.get().strip()
        is_valid = os.path.isdir(path_str)

        if is_valid:
            self.button_start.config(state=tk.NORMAL)
            self.status_var.set(f"Klasör hazır: {os.path.basename(path_str)}")
            self.status_label.config(foreground="green")
        else:
            self.button_start.config(state=tk.DISABLED)
            if path_str:
                self.status_var.set("HATA: Klasör yolu geçerli değil.")
                self.status_label.config(foreground="red")
            else:
                self.status_var.set("Lütfen bir klasör seçin.")
                self.status_label.config(foreground="black")

    def update_status(self, message, is_error=False, log_only=False):
        """GUI'daki durumu güncelleyen ve log alanına yazan yardımcı fonksiyon."""

        # Log alanına yazma
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)  # En alta kaydır
        self.log_text.config(state=tk.DISABLED)

        # Ana durum etiketini güncelleme (Log sadece istenirse atla)
        if not log_only:
            self.status_var.set(message)
            self.status_label.config(foreground="red" if is_error else "blue")

        self.master.update_idletasks()

    def start_processing_thread(self):
        """Ana iş parçacığını engellememek için işlemi ayrı bir thread'de başlatır."""

        # Arayüzü kilitle
        self.button_start.config(state=tk.DISABLED, text="İşleniyor...")
        self.button_browse.config(state=tk.DISABLED)
        self.progress_bar.start(10)  # İlerleme çubuğunu başlat

        self.update_status("İşlem Başlatıldı. Detaylar için logları kontrol edin...", log_only=False)
        self.update_status("--------------------------------------------------", log_only=True)

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
            final_message = f"🎉 İşlem Tamamlandı! Toplam {self.total_conversions} dosya çözüldü. Süre: {end_time - start_time:.2f} saniye."
            self.update_status(final_message, log_only=False)
            messagebox.showinfo("İşlem Başarılı", final_message)

        except Exception as e:
            error_message = f"KRİTİK HATA: İşlem sırasında bir sorun oluştu: {e}"
            self.update_status(error_message, is_error=True)
            messagebox.showerror("Hata", error_message)

        self.reset_gui()

    def reset_gui(self):
        """GUI'yı başlangıç durumuna döndürür."""
        self.progress_bar.stop()
        self.button_browse.config(state=tk.NORMAL)
        self.check_path_validity()

    # --- Ana Çalıştırma ---


if __name__ == "__main__":
    root = tk.Tk()
    app = ApkConverterApp(root)
    root.mainloop()