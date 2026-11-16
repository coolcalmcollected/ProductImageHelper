# Product Image Helper - 600×600 White Canvas Formatter

An automated AI-powered tool designed for e-commerce, cataloging, and product photography. It strips all backgrounds, harsh cast shadows, reflections, and stray markings, isolates the product subject, and centers it onto a clean **600×600 pure white (`#FFFFFF`) canvas** with a crisp **5% margin**.

---

## ✨ Features

- **Advanced AI Segmentation**: Powered by **BiRefNet** (*Bilateral Reference Network*, 2024 SOTA), with support for **U2-Net** and **IS-Net**. Accurately separates product packaging from complex, patterned, or illustrated backdrops without clipping corners or leaving halos.
- **Edge Defringing (Matte Choking)**: Shaves off the 1-pixel boundary transition where shadows bleed into the product edges, producing natural, clean packaging edges without dark borders.
- **Upscaling & Pixelation Protection**: Intelligently scales down large images to fit the 600×600 canvas while preventing small images from being forcibly stretched, maintaining 100% native sharpness.
- **Aspect-Preserving 600×600 Framing**: Calculates the optimal scale to fit within 600×600 without distortion.
- **5% Border Margin**: Automatically leaves a neat 5% margin (540×540 inner product box) so the product never touches the canvas edges.
- **Pure White Background (`#FFFFFF`)**: Blended with high-quality Lanczos resampling and anti-aliasing.
- **Browser-Based Interface**:
  - Native Windows **"Browse..."** folder picker dialogs for input and output directories.
  - Interactive parameter controls: Canvas dimensions, margin slider, background color picker, format (JPEG / PNG / WEBP), upscale limit, and defringe intensity.
  - Real-time progress bar with live file tracking.
  - Interactive Before/After gallery cards with side-by-side zoom modal comparison.
  - Direct "Open Output Folder" button to open the cleaned images in Windows Explorer.
- **Headless CLI Support**: Scriptable batch command-line interface.
- **100% Offline & Private**: All models and processing run locally on your machine with zero cloud upload.

---

## 🚀 Getting Started

### Installation

Clone the repository and install dependencies:
```bash
git clone https://github.com/coolcalmcollected/ProductImageHelper.git
cd ProductImageHelper

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Running the App

#### Windows
Double-click `run.bat`, or run:
```bash
.\venv\Scripts\python.exe app.py 5055
```
This launches the local server and opens `http://127.0.0.1:5055` in your web browser.

#### macOS (Browser Mode)
Make `run.command` executable once (`chmod +x run.command`) and double-click it in Finder, or run:
```bash
./run.command
```

#### macOS (Standalone `.app` Bundle)
To build a standalone `ProductImageHelper.app` you can drag into `/Applications`:
```bash
chmod +x build_mac_app.sh
./build_mac_app.sh
```
This packages the app with a native macOS window (`pywebview`) into `dist/ProductImageHelper.app`. On first run, the AI model weights download to `~/Library/Application Support/ProductImageHelper/`.

#### Option 2: Command Line (CLI)
Batch process images directly from the terminal:
```bash
.\venv\Scripts\python.exe cli.py --input "C:\path\to\raw_images" --output "C:\path\to\cleaned" --size 600 --margin 5 --model birefnet-general
```

##### CLI Flags:
- `-i, --input`: Path to directory containing raw product images (Required).
- `-o, --output`: Destination directory (Default: `<input>/cleaned_600x600`).
- `-s, --size`: Square canvas size in pixels (Default: `600`).
- `-m, --margin`: Margin percentage around the product (Default: `5.0`).
- `-f, --format`: Output format: `JPEG`, `PNG`, or `WEBP` (Default: `JPEG`).
- `-q, --quality`: Image quality from 1 to 100 (Default: `95`).
- `-u, --max-upscale`: Max upscale factor (Default: `1.0` = do not upscale small images to avoid pixelation).
- `-d, --defringe`: Defringe pixel choke to eliminate dark edge halos (Default: `1`).
- `--model`: AI model: `birefnet-general` (Default), `u2net`, or `isnet-general-use`.

---

## 📁 Project Structure

```
ProductImageHelper/
├── cleaner.py          # Core AI background & shadow stripper + 600x600 compositor
├── app.py              # Web application backend server (REST API + Folder Picker)
├── cli.py              # Command-line interface for automated batch processing
├── run.bat             # One-click Windows launcher
├── static/
│   └── index.html      # Responsive web UI with live gallery & controls
├── samples/
│   ├── input/          # Sample images for testing
│   └── output/         # Cleaned 600x600 output images
├── requirements.txt    # Project Python dependencies
└── .gitignore          # Git ignore rules for venv, models, and cache
```
