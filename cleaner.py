import os
import sys
from pathlib import Path
from PIL import Image, ImageFilter

# Ensure local models folder is used by rembg
WORKSPACE_DIR = Path(__file__).resolve().parent
os.environ["U2NET_HOME"] = str(WORKSPACE_DIR)

import rembg

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}

class ProductImageCleaner:
    def __init__(self, default_model: str = "birefnet-general"):
        self.default_model = default_model
        self._sessions = {}

    def get_session(self, model_name: str | None = None):
        name = model_name or self.default_model
        if name not in self._sessions:
            print(f"Loading session for model '{name}'...")
            self._sessions[name] = rembg.new_session(name)
        return self._sessions[name]

    def clean_and_resize(
        self,
        input_image_path: str | Path,
        output_image_path: str | Path,
        target_size: int = 600,
        margin_pct: float = 0.05,
        bg_color: tuple[int, int, int] = (255, 255, 255),
        output_format: str = "JPEG",
        quality: int = 95,
        max_upscale: float = 1.0,
        defringe_pixels: int = 1,
        model_name: str = "birefnet-general",
    ) -> dict:
        """
        Processes a single product image:
        1. Strips background and cast shadows using neural segmentation.
        2. Applies alpha defringing (matte choke + feather) to eliminate dark boundary halos.
        3. Crops to tight product bounding box.
        4. Scales to fit target box with margin, capping upscale at max_upscale (default 1.0)
           to prevent pixelation on smaller images.
        5. Centers product on pure white square canvas.
        """
        input_path = Path(input_image_path)
        output_path = Path(output_image_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        session = self.get_session(model_name)

        with Image.open(input_path) as raw_img:
            # Handle orientation if EXIF present
            try:
                from PIL import ImageOps
                raw_img = ImageOps.exif_transpose(raw_img)
            except Exception:
                pass

            rgb_img = raw_img.convert("RGB")
            orig_w, orig_h = rgb_img.size

            # AI Segmentation: remove background and shadows
            rgba = rembg.remove(rgb_img, session=session)
            r, g, b, alpha = rgba.split()

            # Defringe / Matte Choke: eliminates dark borders/halos absorbed from original shadows
            if defringe_pixels > 0:
                filter_size = 3 if defringe_pixels == 1 else (2 * defringe_pixels + 1)
                # Contract the alpha mask slightly to cut away the shadow-bleed transition pixels
                eroded_alpha = alpha.filter(ImageFilter.MinFilter(filter_size))
                # Gentle sub-pixel Gaussian blur for silky smooth anti-aliased edges
                eroded_alpha = eroded_alpha.filter(ImageFilter.GaussianBlur(0.4))
                rgba.putalpha(eroded_alpha)
                alpha = eroded_alpha

            # Auto-trim to tight bounding box of product
            bbox = alpha.getbbox()
            cropped = rgba.crop(bbox) if bbox else rgba

            cw, ch = cropped.size
            if cw == 0 or ch == 0:
                cropped = rgba
                cw, ch = cropped.size

            # Calculate target inner bounding box
            inner_w = max(10, int(target_size * (1.0 - 2 * margin_pct)))
            inner_h = inner_w

            # Base scale factor to fit inside inner box
            scale = min(inner_w / cw, inner_h / ch)

            # Prevent upscaling small images past max_upscale (default 1.0 = 100% native size)
            # This completely avoids pixelation / blurriness on low-res images!
            if max_upscale is not None and max_upscale > 0:
                scale = min(scale, max_upscale)

            new_w = max(1, int(round(cw * scale)))
            new_h = max(1, int(round(ch * scale)))

            resized_product = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Create square canvas with solid background (pure white #FFFFFF)
            canvas = Image.new("RGB", (target_size, target_size), bg_color)
            paste_x = (target_size - new_w) // 2
            paste_y = (target_size - new_h) // 2

            # Alpha composite onto white canvas
            canvas.paste(resized_product, (paste_x, paste_y), mask=resized_product.split()[-1])

            # Save result
            fmt = output_format.upper()
            if fmt == "JPG":
                fmt = "JPEG"

            save_kwargs = {}
            if fmt == "JPEG":
                save_kwargs["quality"] = quality
                save_kwargs["subsampling"] = 0  # 4:4:4 for razor-sharp details
            elif fmt == "WEBP":
                save_kwargs["quality"] = quality

            canvas.save(output_path, fmt, **save_kwargs)

            return {
                "input_file": str(input_path),
                "output_file": str(output_path),
                "original_size": [orig_w, orig_h],
                "cropped_product_size": [cw, ch],
                "output_size": [target_size, target_size],
                "scaled_size": [new_w, new_h],
                "scale_factor": round(scale, 3),
                "upscaled": scale > 1.0,
                "model_used": model_name,
                "status": "success",
            }

    @staticmethod
    def scan_directory(directory: str | Path) -> list[Path]:
        """Scans a directory for supported image files."""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            return []
        files = []
        for p in dir_path.iterdir():
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(p)
        return sorted(files, key=lambda f: f.name.lower())
