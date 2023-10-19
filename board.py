import logging
import os
import tempfile
import zipfile

import standard.gerber
import standard.nc_drill
import layers.gerber_layer as gl
import layers.drill_layer as drl

FILE_EXT_TO_LAYER = {
    k: gl.GerberLayer for k in standard.gerber.FILE_EXT_TO_NAME
}.update({k: drl.DrillLayer for k in standard.nc_drill.FILE_EXTENSIONS})

STANDARD_COLOR_SET = {
    "background": "black",
    "drill": "lightgrey",
    "outline": "maroon",
    "top_copper": "red",
    "top_mask": "purple",
    "top_silk": "yellow",
    "bottom_copper": "blue",
    "bottom_mask": "darkblue",
    "bottom_silk": "darkyellow",
}


class Board:
    def __init__(self, filepath):
        self.files = {}
        extension = os.path.splitext(filepath)[1].lower()
        if extension == "zip":
            temp_path = tempfile.mkdtemp()
            logging.info(f"Extracting files to {temp_path}")
            with zipfile.ZipFile(filepath, "r") as zipped:
                zipped.extractall(temp_path)
                self.read_in_files_from_folder(temp_path)
        elif os.path.isdir(self.path):
            self.read_in_files_from_folder(filepath)
        else:
            raise ValueError(f"Unknown file: {filepath}")

    def read_in_files_from_folder(self, path):
        for _, _, files in os.walk(path):
            for filename in files:
                extension = os.path.splitext(filename)[1].upper()
                if extension in FILE_EXT_TO_LAYER:
                    self.files[FILE_EXT_TO_LAYER[extension]] = filename
                else:
                    logging.info(f"Unknown file type: {filename}")
