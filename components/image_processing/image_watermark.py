import argparse

from components.image_processing.utils import add_watermark


def arg_parser():
    parser = argparse.ArgumentParser(description="Add a watermark to an image.")
    parser.add_argument("input_image", help="Path to the base image")
    parser.add_argument("watermark_image", help="Path to the watermark image")
    parser.add_argument("-o", "--output", default="output_with_watermark.png", help="Output file path")
    parser.add_argument("--opacity", type=float, default=0.8, help="Watermark opacity (0.0-1.0)")
    return parser.parse_args()


if __name__ == "__main__":
    add_watermark(arg_parser())
