import argparse

from components.image_processing.image_utils import add_watermark


def arg_parser():
    parser = argparse.ArgumentParser(description="Add a watermark to an image.")
    parser.add_argument("input_image_folder", help="Path to the folder with images")
    parser.add_argument("watermark_image", help="Path to the watermark image")
    parser.add_argument("-o", "--output", default="", help="Output folder path")
    parser.add_argument("--opacity", type=float, default=0.8, help="Watermark opacity (0.0-1.0)")
    parser.add_argument("--rescale", type=bool, default=False, help="Watermark should be resize to 200x100px")
    return parser.parse_args()


if __name__ == "__main__":
    add_watermark(arg_parser())
