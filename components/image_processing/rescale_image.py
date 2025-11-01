import argparse
import os

from components.image_processing.utils import downscale_image


def arg_parser():
    parser = argparse.ArgumentParser(description="Add a watermark to an image.")
    parser.add_argument("input_folder", help="Path to the folder with images")
    parser.add_argument("output_folder", help="Output folder path")

    return parser.parse_args()


if __name__ == "__main__":
    args = arg_parser()
    os.makedirs(args.output_folder, exist_ok=True)

    for image in os.listdir(args.input_folder):
        if ".png" in image:
            # Example usage:
            # Downscale by 50%
            downscale_image(
                os.path.join(args.input_folder, image), os.path.join(args.output_folder, image), scale_factor=0.5
            )
            # Or resize to fit within 800x600 while keeping proportions
            # downscale_image("input.jpg", "output_max.jpg", max_size=(800, 600))
