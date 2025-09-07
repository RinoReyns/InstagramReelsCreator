import os

from main import logger


def check_if_file_exists(folder, file):
    if folder != "":
        full_path = os.path.join(folder, file)
        if not os.path.exists(full_path):
            logger.warning(f"Warning: file not found {full_path}")
