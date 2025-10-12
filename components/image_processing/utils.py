from PIL import Image


def add_watermark(args):
    # Load base image and watermark
    base = Image.open(args.input_image).convert("RGBA")
    watermark = Image.open(args.watermark_image).convert("RGBA")

    # Apply opacity to watermark
    alpha = watermark.split()[3]  # extract alpha channel
    alpha = alpha.point(lambda p: int(p * args.opacity))
    watermark.putalpha(alpha)

    x = base.width - watermark.width - 20
    y = base.height - watermark.height - 20

    # Paste watermark using transparency
    base.paste(watermark, (x, y), watermark)

    # Save result
    base.save(args.output)
    print(f"Watermarked image saved to {args.output}")
