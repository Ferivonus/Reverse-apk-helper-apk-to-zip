import os
import shutil
import zipfile
from pathlib import Path
import time
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import threading

# Global Variables
ROOT_PATH = None


# --- FILE PROCESSING LOGIC ---

def process_folder_recursively(folder_path: Path, extensions: tuple, status_update_func) -> int:
    """
    Converts APKs in the specified folder to ZIP copies, extracts them,
    deletes the ZIPs, and recursively calls itself for the extracted folders.
    """
    global ROOT_PATH
    if not folder_path.is_dir():
        return 0

    total_files_processed = 0
    zip_files_list = []

    # 1. Create ZIP copies of APKs in the current folder
    for file_name in os.listdir(folder_path):
        original_path = folder_path / file_name

        if original_path.is_file() and original_path.suffix.lower() in extensions:

            original_suffix_clean = original_path.suffix.strip('.').lower()
            # Use a distinctive name to avoid conflicts and track the original type
            new_file_name = f"{original_path.stem}_{original_suffix_clean}_old-package.zip"
            new_zip_path = original_path.with_name(new_file_name)

            # Skip if the ZIP copy already exists (partially processed scenario)
            if new_zip_path.exists():
                zip_files_list.append(new_zip_path)
                continue

            try:
                shutil.copy2(original_path, new_zip_path)
                zip_files_list.append(new_zip_path)
                total_files_processed += 1

                relative_path = new_zip_path.relative_to(ROOT_PATH)
                status_update_func(f"[Created ZIP] -> {relative_path}", log_only=True)

            except Exception as e:
                status_update_func(f"ERROR: Could not copy '{original_path.name}': {e}", is_error=True)

    # 2. Extract the created ZIP files and 3. Delete the ZIP
    extracted_folders = []

    for zip_path in zip_files_list:
        extract_dir_name = zip_path.stem
        extract_dir = zip_path.with_name(extract_dir_name)

        # Only extract if the destination folder doesn't exist
        if not extract_dir.exists():
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                extracted_folders.append(extract_dir)

                relative_path = zip_path.relative_to(ROOT_PATH)
                status_update_func(f"[Extracted and Deleted ZIP] -> {relative_path}", log_only=True)

            except Exception as e:
                status_update_func(f"ERROR: Could not extract '{zip_path.name}': {e}", is_error=True)

            finally:
                # Delete the ZIP file immediately after extraction
                try:
                    os.remove(zip_path)
                except Exception as e:
                    status_update_func(f"CRITICAL ERROR: Could not delete '{zip_path.name}'! Error: {e}", is_error=True)

        # If the folder already exists, just delete the ZIP copy to clean up
        elif zip_path.exists():
            try:
                os.remove(zip_path)
            except Exception as e:
                status_update_func(
                    f"CRITICAL ERROR: Could not delete '{zip_path.name}' when destination folder existed! Error: {e}",
                    is_error=True)

    # 4. Call the function again for every newly extracted folder (Recursion)
    for new_folder in extracted_folders:
        total_files_processed += process_folder_recursively(new_folder, extensions, status_update_func)

    return total_files_processed


# --- TKINTER GUI CLASS ---

class ApkConverterApp:
    def __init__(self, master):
        self.master = master
        master.title("Recursive APK Resolver Tool (v2.0)")
        master.geometry("700x550")

        self.total_conversions = 0
        global ROOT_PATH
        ROOT_PATH = None

        # Main container frame
        self.main_frame = ttk.Frame(master, padding="10 10 10 10")
        self.main_frame.pack(fill='both', expand=True)

        # 1. Input/Control Frame
        self.control_frame = ttk.LabelFrame(self.main_frame, text="Control Panel", padding="10")
        self.control_frame.grid(row=0, column=0, sticky="ew", pady=10)
        self.control_frame.grid_columnconfigure(1, weight=1)  # Allow entry field to expand

        # Folder Selection
        ttk.Label(self.control_frame, text="Folder Path:", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5,
                                                                                            pady=5, sticky="w")

        self.entry_path = ttk.Entry(self.control_frame, width=70)
        self.entry_path.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.button_browse = ttk.Button(self.control_frame, text="Browse", command=self.browse_folder)
        self.button_browse.grid(row=0, column=2, padx=5, pady=5)

        # Start Processing Button
        self.button_start = ttk.Button(self.control_frame, text="START Process", command=self.start_processing_thread,
                                       state=tk.DISABLED, style='Accent.TButton')
        self.button_start.grid(row=1, column=1, pady=10, sticky="ew")

        # 2. Status and Progress Frame
        self.status_frame = ttk.Frame(self.main_frame, padding="5")
        self.status_frame.grid(row=1, column=0, sticky="ew", pady=5)
        self.status_frame.grid_columnconfigure(0, weight=1)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(self.status_frame, orient='horizontal', mode='indeterminate', length=650)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=5)

        # General Status Label
        self.status_var = tk.StringVar()
        self.status_var.set("Please select a folder.")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var, font=('Arial', 10, 'italic'),
                                      anchor=tk.W)
        self.status_label.grid(row=1, column=0, sticky="ew")

        # 3. Log Frame
        self.log_frame = ttk.LabelFrame(self.main_frame, text="Process Logs", padding="10")
        self.log_frame.grid(row=2, column=0, sticky="nsew", pady=10)
        self.main_frame.grid_rowconfigure(2, weight=1)  # Allow log area to expand vertically
        self.log_frame.grid_columnconfigure(0, weight=1)

        # Log Text Area (Scrollable)
        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap=tk.WORD, width=80, height=15,
                                                  font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.config(state=tk.DISABLED)  # Make read-only

        # Configure Tkinter style (optional, for a cleaner look)
        s = ttk.Style()
        s.theme_use('clam')  # 'clam' or 'alt' are modern themes
        s.configure('Accent.TButton', foreground='white', background='#0078D4')

        # Track changes in the entry field
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
            self.status_var.set(f"Folder ready: {os.path.basename(path_str)}")
            self.status_label.config(foreground="green")
        else:
            self.button_start.config(state=tk.DISABLED)
            if path_str:
                self.status_var.set("ERROR: Folder path is not valid.")
                self.status_label.config(foreground="red")
            else:
                self.status_var.set("Please select a folder.")
                self.status_label.config(foreground="black")

    def update_status(self, message, is_error=False, log_only=False):
        """Helper function to update GUI status and write to the log area."""

        # Write to log area
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)  # Scroll to the bottom
        self.log_text.config(state=tk.DISABLED)

        # Update main status label (Skip if log_only is requested)
        if not log_only:
            self.status_var.set(message)
            self.status_label.config(foreground="red" if is_error else "blue")

        self.master.update_idletasks()

    def start_processing_thread(self):
        """Starts the process in a separate thread to prevent blocking the main thread."""

        # Lock the GUI
        self.button_start.config(state=tk.DISABLED, text="Processing...")
        self.button_browse.config(state=tk.DISABLED)
        self.progress_bar.start(10)  # Start the indeterminate progress bar

        self.update_status("Process Started. Check logs for details...", log_only=False)
        self.update_status("--------------------------------------------------", log_only=True)

        # Move the processing logic to a new thread
        processing_thread = threading.Thread(target=self.run_main_process)
        processing_thread.start()

    def run_main_process(self):
        """Runs the file processing logic (inside the thread)."""
        global ROOT_PATH
        folder_path_str = self.entry_path.get().strip()

        try:
            folder_path = Path(folder_path_str).resolve()
            ROOT_PATH = folder_path
        except Exception:
            self.update_status(f"ERROR: Invalid path: {folder_path_str}", is_error=True)
            self.reset_gui()
            return

        start_time = time.time()

        try:
            # Start the processing function, passing the status update callback
            self.total_conversions = process_folder_recursively(
                folder_path,
                extensions=('.apk', '.apkm', '.xapk'),
                status_update_func=self.update_status
            )

            # Successful completion
            end_time = time.time()
            final_message = f"🎉 Process Complete! Total {self.total_conversions} packages resolved. Duration: {end_time - start_time:.2f} seconds."
            self.update_status(final_message, log_only=False)
            messagebox.showinfo("Process Successful", final_message)

        except Exception as e:
            error_message = f"CRITICAL ERROR: An issue occurred during the process: {e}"
            self.update_status(error_message, is_error=True)
            messagebox.showerror("Error", error_message)

        self.reset_gui()

    def reset_gui(self):
        """Resets the GUI to the starting state."""
        self.progress_bar.stop()
        self.button_browse.config(state=tk.NORMAL)
        self.check_path_validity()


# --- Main Execution ---


if __name__ == "__main__":
    root = tk.Tk()
    app = ApkConverterApp(root)
    root.mainloop()