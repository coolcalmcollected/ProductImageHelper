import argparse
import sys
from pathlib import Path
from cleaner import ProductImageCleaner

def main():
    parser = argparse.ArgumentParser(description="Clean and format product images to 600x600 pure white canvas.")
    parser.add_argument("-i", "--input", required=True, help="Path to input directory containing images")
    parser.add_argument("-o", "--output", default="", help="Path to output directory (default: <input>/cleaned_600x600)")
    parser.add_argument("-s", "--size", type=int, default=600, help="Target canvas square size (default: 600)")
    parser.add_argument("-m", "--margin", type=float, default=5.0, help="Margin percentage (default: 5.0 for 5%%)")
    parser.add_argument("-f", "--format", default="JPEG", choices=["JPEG", "PNG", "WEBP"], help="Output image format")
    parser.add_argument("-q", "--quality", type=int, default=95, help="JPEG/WEBP quality 1-100 (default: 95)")
    parser.add_argument("-u", "--max-upscale", type=float, default=1.0, help="Max upscale factor (default: 1.0 = do not upscale small images)")
    parser.add_argument("-d", "--defringe", type=int, default=1, help="Defringe pixels to eliminate dark edge halos (default: 1)")
    parser.add_argument("--model", default="birefnet-general", choices=["birefnet-general", "u2net", "isnet-general-use"], help="AI segmentation model (default: birefnet-general)")
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: Input directory does not exist: {input_dir}")
        sys.exit(1)

    output_dir = Path(args.output) if args.output else input_dir / "cleaned_600x600"
    output_dir.mkdir(parents=True, exist_ok=True)

    files = ProductImageCleaner.scan_directory(input_dir)
    if not files:
        print(f"No supported images found in {input_dir}")
        sys.exit(0)

    print(f"Found {len(files)} image(s) to process.")
    print(f"Settings: Size={args.size}x{args.size}, Margin={args.margin}%, MaxUpscale={args.max_upscale}x, Defringe={args.defringe}px")
    print(f"Output directory: {output_dir}")
    print("-" * 50)

    cleaner = ProductImageCleaner()
    ext = ".jpg" if args.format in ("JPEG", "JPG") else f".{args.format.lower()}"

    success_count = 0
    for idx, f in enumerate(files, start=1):
        out_file = output_dir / f"{f.stem}_cleaned{ext}"
        print(f"[{idx}/{len(files)}] Cleaning {f.name}...", end=" ", flush=True)
        try:
            res = cleaner.clean_and_resize(
                input_image_path=f,
                output_image_path=out_file,
                target_size=args.size,
                margin_pct=args.margin / 100.0,
                output_format=args.format,
                quality=args.quality,
                max_upscale=args.max_upscale if args.max_upscale > 0 else None,
                defringe_pixels=args.defringe,
                model_name=args.model,
            )
            success_count += 1
            print(f"OK -> {out_file.name} (scale: {res['scale_factor']}x)")
        except Exception as e:
            print(f"FAILED: {e}")

    print("-" * 50)
    print(f"Finished! Successfully cleaned {success_count}/{len(files)} images.")

if __name__ == "__main__":
    main()
