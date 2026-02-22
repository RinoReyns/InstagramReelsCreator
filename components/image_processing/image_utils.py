import logging
import os

from PIL import Image, ImageOps

from utils.data_structures import IMAGE_EXTENSIONS

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
logger = logging.getLogger(__name__)


def add_watermark(args):
    # Load base image and watermark
    os.makedirs(args.output, exist_ok=True)
    for image in os.listdir(args.input_image_folder):
        if image.split(".")[-1] not in IMAGE_EXTENSIONS:
            continue
        image_path = os.path.join(args.input_image_folder, image)
        logging.info(image_path)
        base = Image.open(image_path)
        base = ImageOps.exif_transpose(base).convert("RGBA")
        watermark = Image.open(args.watermark_image).convert("RGBA")
        if args.rescale:
            watermark = rescale_image(watermark)
        # Apply opacity to watermark
        alpha = watermark.split()[3]  # extract alpha channel
        alpha = alpha.point(lambda p: int(p * args.opacity))
        watermark.putalpha(alpha)

        x = base.width - watermark.width - 20
        y = base.height - watermark.height - 20

        # Paste watermark using transparency
        base.paste(watermark, (x, y), watermark)

        # Save result
        file_name, _ = os.path.basename(image_path).split('.')
        output_path = os.path.join(args.output, f"{file_name}_watermark.png")
        base.save(output_path)
        logging.info(f"Watermarked image saved to {output_path}")


def rescale_image(watermark):
    max_width = 300
    max_height = 100
    scale = min(max_width / watermark.width, max_height / watermark.height)
    # Compute new size
    new_size = (int(watermark.width * scale), int(watermark.height * scale))
    # Resize the image
    watermark = watermark.resize(new_size, Image.Resampling.LANCZOS)
    return watermark


def downscale_image(input_path, output_path, scale_factor=None, max_size=None):
    """
    Downscale an image while keeping its original proportions.

    Parameters:
    - input_path: str, path to the input image
    - output_path: str, path to save the downscaled image
    - scale_factor: float, e.g., 0.5 to reduce by 50%
    - max_size: tuple (max_width, max_height), optional maximum dimensions
    """
    # Open the image
    img = Image.open(input_path)
    width, height = img.size

    # Calculate new size
    if scale_factor:
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
    elif max_size:
        max_width, max_height = max_size
        # Calculate scale factor to fit within max_size while preserving aspect ratio
        scale = min(max_width / width, max_height / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
    else:
        raise ValueError("Either scale_factor or max_size must be provided")

    # Resize with high-quality downscaling
    img_resized = img.resize((new_width, new_height), Image.LANCZOS)

    # Save the downscaled image
    img_resized.save(output_path)
    print(f"Image saved: {output_path} ({new_width}x{new_height})")
