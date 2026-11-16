import os
import sys
import json
import uuid
import queue
import mimetypes
import threading
import subprocess
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

from cleaner import ProductImageCleaner, SUPPORTED_EXTENSIONS

PORT = 5055

def get_static_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "static"
    return Path(__file__).resolve().parent / "static"

STATIC_DIR = get_static_dir()

# Global state for jobs
cleaner_instance = ProductImageCleaner()
active_jobs = {}
job_workers = {}
jobs_lock = threading.Lock()

def open_native_folder_picker(initial_dir=""):
    """Opens a native OS folder selection dialog (thread-safe on Windows & macOS)."""
    try:
        if sys.platform == "darwin":
            if initial_dir and os.path.exists(initial_dir):
                script = (
                    "on run argv\n"
                    "set initDir to POSIX file (item 1 of argv)\n"
                    'return POSIX path of (choose folder with prompt "Select Image Folder" default location initDir)\n'
                    "end run"
                )
                cmd = ["osascript", "-e", script, initial_dir]
            else:
                script = 'return POSIX path of (choose folder with prompt "Select Image Folder")'
                cmd = ["osascript", "-e", script]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                chosen = res.stdout.strip()
                if len(chosen) > 1:
                    chosen = chosen.rstrip("/")
                return chosen
            return ""

        elif sys.platform.startswith("linux"):
            cmd = ["zenity", "--file-selection", "--directory", "--title=Select Image Folder"]
            if initial_dir and os.path.exists(initial_dir):
                cmd.append(f"--filename={initial_dir.rstrip('/')}/")
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                return res.stdout.strip()
            return ""

        else:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(
                initialdir=initial_dir if os.path.exists(initial_dir) else None,
                title="Select Image Folder"
            )
            root.destroy()
            return folder or ""
    except Exception as e:
        print(f"Error opening folder picker: {e}")
        return ""

def open_folder_in_file_manager(folder_path: str):
    """Opens a folder in Windows Explorer, macOS Finder, or Linux file manager."""
    if sys.platform == "win32":
        os.startfile(folder_path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", folder_path])
    else:
        subprocess.Popen(["xdg-open", folder_path])

class BatchJobWorker(threading.Thread):
    def __init__(self, job_id: str, config: dict):
        super().__init__(daemon=True)
        self.job_id = job_id
        self.config = config
        self.is_cancelled = False

    def run(self):
        input_dir = Path(self.config["input_dir"])
        output_dir = Path(self.config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        target_size = int(self.config.get("target_size", 600))
        margin_pct = float(self.config.get("margin_pct", 0.05))
        output_format = self.config.get("format", "JPEG").upper()
        quality = int(self.config.get("quality", 95))
        bg_hex = self.config.get("bg_color", "#FFFFFF").lstrip("#")
        
        max_upscale_val = self.config.get("max_upscale", 1.0)
        max_upscale = float(max_upscale_val) if max_upscale_val is not None and float(max_upscale_val) > 0 else None
        defringe_pixels = int(self.config.get("defringe_pixels", 1))
        model_name = self.config.get("model_name", "birefnet-general")

        try:
            bg_color = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            bg_color = (255, 255, 255)

        files = ProductImageCleaner.scan_directory(input_dir)
        total = len(files)

        with jobs_lock:
            active_jobs[self.job_id]["total"] = total
            active_jobs[self.job_id]["status"] = "running"

        ext = ".jpg" if output_format in ("JPEG", "JPG") else f".{output_format.lower()}"

        for idx, file_path in enumerate(files):
            if self.is_cancelled:
                with jobs_lock:
                    active_jobs[self.job_id]["status"] = "cancelled"
                return

            with jobs_lock:
                active_jobs[self.job_id]["current"] = idx + 1
                active_jobs[self.job_id]["current_file"] = file_path.name

            out_file = output_dir / f"{file_path.stem}_cleaned{ext}"

            try:
                result = cleaner_instance.clean_and_resize(
                    input_image_path=file_path,
                    output_image_path=out_file,
                    target_size=target_size,
                    margin_pct=margin_pct,
                    bg_color=bg_color,
                    output_format=output_format,
                    quality=quality,
                    max_upscale=max_upscale,
                    defringe_pixels=defringe_pixels,
                    model_name=model_name,
                )
                with jobs_lock:
                    active_jobs[self.job_id]["results"].append({
                        "filename": file_path.name,
                        "input_path": str(file_path),
                        "output_path": str(out_file),
                        "output_name": out_file.name,
                        "status": "success",
                        "details": result,
                    })
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
                with jobs_lock:
                    active_jobs[self.job_id]["results"].append({
                        "filename": file_path.name,
                        "input_path": str(file_path),
                        "output_path": "",
                        "output_name": "",
                        "status": "error",
                        "error": str(e),
                    })

        with jobs_lock:
            active_jobs[self.job_id]["status"] = "completed"
            active_jobs[self.job_id]["current_file"] = ""

class AppRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/status":
            self.send_json({"status": "ok", "app": "ProductImageHelper"})
            return

        elif path.startswith("/api/job/"):
            job_id = path.replace("/api/job/", "").strip()
            with jobs_lock:
                job = active_jobs.get(job_id)
                if job:
                    job_data = {
                        "id": job["id"],
                        "input_dir": job["input_dir"],
                        "output_dir": job["output_dir"],
                        "status": job["status"],
                        "total": job["total"],
                        "current": job["current"],
                        "current_file": job["current_file"],
                        "results": list(job.get("results", [])),
                    }
                else:
                    job_data = None
            if not job_data:
                self.send_json({"error": "Job not found"}, status=404)
            else:
                self.send_json(job_data)
            return

        elif path == "/api/image":
            image_path_str = query.get("path", [""])[0]
            if not image_path_str:
                self.send_error(400, "Missing path parameter")
                return

            img_path = Path(unquote(image_path_str))
            if not img_path.exists() or not img_path.is_file():
                self.send_error(404, "File not found")
                return

            mime_type, _ = mimetypes.guess_type(str(img_path))
            if not mime_type:
                mime_type = "application/octet-stream"

            try:
                with open(img_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, f"Error reading file: {e}")
            return

        elif path == "/":
            self.path = "/index.html"
            return super().do_GET()

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            data = json.loads(post_body.decode("utf-8")) if post_body else {}
        except Exception:
            data = {}

        if path == "/api/browse":
            init_dir = data.get("initial_dir", "")
            chosen = open_native_folder_picker(init_dir)
            self.send_json({"path": chosen})
            return

        elif path == "/api/scan":
            target_dir = data.get("dir", "")
            if not target_dir or not os.path.exists(target_dir):
                self.send_json({"count": 0, "files": [], "error": "Directory does not exist"})
                return

            files = ProductImageCleaner.scan_directory(target_dir)
            self.send_json({
                "count": len(files),
                "files": [f.name for f in files],
                "dir": str(Path(target_dir).resolve())
            })
            return

        elif path == "/api/process":
            input_dir = data.get("input_dir", "").strip()
            output_dir = data.get("output_dir", "").strip()

            if not input_dir or not os.path.exists(input_dir):
                self.send_json({"error": "Input directory does not exist"}, status=400)
                return

            if not output_dir:
                output_dir = str(Path(input_dir) / "cleaned_600x600")

            job_id = str(uuid.uuid4())
            with jobs_lock:
                active_jobs[job_id] = {
                    "id": job_id,
                    "input_dir": input_dir,
                    "output_dir": output_dir,
                    "status": "pending",
                    "total": 0,
                    "current": 0,
                    "current_file": "",
                    "results": [],
                }

            worker = BatchJobWorker(job_id, {
                "input_dir": input_dir,
                "output_dir": output_dir,
                "target_size": data.get("target_size", 600),
                "margin_pct": data.get("margin_pct", 0.05),
                "format": data.get("format", "JPEG"),
                "quality": data.get("quality", 95),
                "bg_color": data.get("bg_color", "#FFFFFF"),
                "max_upscale": data.get("max_upscale", 1.0),
                "defringe_pixels": data.get("defringe_pixels", 1),
                "model_name": data.get("model_name", "birefnet-general"),
            })
            with jobs_lock:
                job_workers[job_id] = worker
            worker.start()

            self.send_json({"job_id": job_id, "output_dir": output_dir})
            return

        elif path.startswith("/api/cancel/"):
            job_id = path.replace("/api/cancel/", "").strip()
            with jobs_lock:
                worker = job_workers.get(job_id)
                if worker:
                    worker.is_cancelled = True
                if job_id in active_jobs:
                    active_jobs[job_id]["status"] = "cancelling"
            self.send_json({"status": "ok"})
            return

        elif path == "/api/open-folder":
            folder_path = data.get("path", "")
            if folder_path and os.path.exists(folder_path):
                try:
                    open_folder_in_file_manager(folder_path)
                    self.send_json({"status": "ok"})
                except Exception as e:
                    self.send_json({"error": str(e)}, status=500)
            else:
                self.send_json({"error": "Folder not found"}, status=404)
            return

        self.send_error(404, "Endpoint not found")

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

def create_server(port=PORT):
    server_address = ("127.0.0.1", port)
    return ThreadingHTTPServer(server_address, AppRequestHandler)

def run_server(port=PORT):
    httpd = create_server(port)
    actual_port = httpd.server_address[1]
    print(f"ProductImageHelper running at http://127.0.0.1:{actual_port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
