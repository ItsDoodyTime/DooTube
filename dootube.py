import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import os
import sys
import requests
import shutil
import re
import ctypes
from PIL import Image, ImageTk

APP_NAME = "DooTube"
GITHUB_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
YTDLP_DOWNLOAD = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"

process = None
cancel_requested = False


# ---------------------------
# Path Handling
# ---------------------------
def get_app_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_app_directory()
DOWNLOAD_DIR = os.path.join(APP_DIR, "DooTube Downloads")
YTDLP_PATH = os.path.join(APP_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(APP_DIR, "_internal", "ffmpeg.exe")

# ---------------------------
# Logging
# ---------------------------
def log(msg):
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)


# ---------------------------
# Download Folder
# ---------------------------
def ensure_download_folder():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ---------------------------
# Version Check
# ---------------------------
def get_local_version():
    if not os.path.exists(YTDLP_PATH):
        return None
    try:
        result = subprocess.run(
            [YTDLP_PATH, "--version"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except:
        return None


def get_latest_version():
    try:
        response = requests.get(GITHUB_API, timeout=10)
        return response.json()["tag_name"]
    except:
        return None


def update_ytdlp_if_needed():
    log("Checking yt-dlp version...")
    local = get_local_version()
    latest = get_latest_version()

    if latest is None:
        log("Could not check latest version.")
        return

    if local == latest:
        log(f"yt-dlp up to date ({local})")
        return

    log(f"Updating yt-dlp → {latest}")

    try:
        r = requests.get(YTDLP_DOWNLOAD, stream=True)
        temp_path = YTDLP_PATH + ".new"

        with open(temp_path, "wb") as f:
            shutil.copyfileobj(r.raw, f)

        if os.path.exists(YTDLP_PATH):
            os.remove(YTDLP_PATH)

        os.rename(temp_path, YTDLP_PATH)
        log("yt-dlp updated successfully.")
    except Exception as e:
        log(f"Update failed: {e}")


# ---------------------------
# Download Logic
# ---------------------------
def download_video():
    global process, cancel_requested
    cancel_requested = False

    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Enter a YouTube URL.")
        return

    ensure_download_folder()
    update_ytdlp_if_needed()

    audio_only = audio_var.get()

    cmd = [
        YTDLP_PATH,
        url,
        "-P", DOWNLOAD_DIR,
        "--ffmpeg-location", FFMPEG_PATH,
        "--newline",
        "--no-keep-video",
    ]

    if audio_only:
        cmd += [
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "192K"
        ]
    else:
        cmd += [
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "--merge-output-format", "mp4"
        ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    for line in process.stdout:
        if cancel_requested:
            break

        log(line.strip())

        match = re.search(
            r"\[download\]\s+(\d+\.\d+)%.*?of\s+([\d\.]+\w+).*?ETA\s+([\d:]+)",
            line
        )
        if match:
            percent = float(match.group(1))
            size = match.group(2)
            eta = match.group(3)

            progress_bar["value"] = percent
            status_label.config(text=f"{percent:.1f}% of {size} | ETA {eta}")

    process.wait()

    if cancel_requested:
        status_label.config(text="Download canceled.")
        progress_bar["value"] = 0
    else:
        status_label.config(text="Download complete.")
        progress_bar["value"] = 100

    process = None


def threaded_download():
    threading.Thread(target=download_video, daemon=True).start()


# ---------------------------
# Cancel Download
# ---------------------------
def cancel_download():
    global process, cancel_requested
    if process:
        cancel_requested = True
        process.terminate()
        log("Download canceled by user.")


# ---------------------------
# UI
# ---------------------------
root = tk.Tk()
root.title(APP_NAME)
root.geometry("600x520")
root.configure(bg="#1e1e1e")

def get_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(APP_DIR, relative_path)

icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
if os.path.exists(icon_path):
    # Window icon
    root.iconbitmap(icon_path)
    # Taskbar icon
    try:
        import ctypes
        myappid = 'dootube.app.1.0'  # Unique ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass


style = ttk.Style()
style.theme_use("default")
style.configure("TProgressbar", troughcolor="#2b2b2b", background="#4caf50")

# Logo
logo_path = get_resource_path(os.path.join("assets", "DooTube.png"))
if os.path.exists(logo_path):
    try:
        img = Image.open(logo_path)
        img = img.resize((86, 86), Image.Resampling.LANCZOS)
        logo_img = ImageTk.PhotoImage(img)
        logo_label = tk.Label(root, image=logo_img, bg="#1e1e1e")
        logo_label.image = logo_img
        logo_label.pack(pady=(2,0))
    except:
        pass

title = tk.Label(root, text="DooTube Downloader", bg="#1e1e1e", fg="white", font=("Segoe UI", 14))
title.pack(pady=10)

url_label = tk.Label(root, text="Video URL:", bg="#1e1e1e", fg="white", font=("Segoe UI", 10))
url_label.pack(pady=(10, 0))

url_entry = tk.Entry(root, width=70, bg="#2b2b2b", fg="white", insertbackground="white")
url_entry.pack(pady=5)

audio_var = tk.BooleanVar()
audio_checkbox = tk.Checkbutton(
    root,
    text="Audio Only (MP3)",
    variable=audio_var,
    bg="#1e1e1e",
    fg="white",
    selectcolor="#1e1e1e"
)
audio_checkbox.pack()

button_frame = tk.Frame(root, bg="#1e1e1e")
button_frame.pack(pady=10)

download_button = tk.Button(
    button_frame,
    text="Download",
    command=threaded_download,
    bg="#333333",
    fg="white",
    width=12
)
download_button.pack(side="left", padx=5)

cancel_button = tk.Button(
    button_frame,
    text="Cancel",
    command=cancel_download,
    bg="#660000",
    fg="white",
    width=12
)
cancel_button.pack(side="left", padx=5)

progress_bar = ttk.Progressbar(root, length=500, mode="determinate")
progress_bar.pack(pady=5)

status_label = tk.Label(root, text="", bg="#1e1e1e", fg="white")
status_label.pack()

log_box = tk.Text(root, height=15, bg="#121212", fg="#00ff88")
log_box.pack(padx=10, pady=10, fill="both", expand=True)

ensure_download_folder()

root.mainloop()
