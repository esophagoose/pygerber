import zipfile
import os
import tempfile


FILE_EXT_TO_NAME = {
    'DRL': 'drill',
    'XLN': 'drill',
    'GKO': 'outline',
    'GM1': 'outline',
    'GTL': 'top_copper',
    'GTS': 'top_mask',
    'GTO': 'top_silk',
    'GBL': 'bottom_copper',
    'GBS': 'bottom_mask',
    'GBO': 'bottom_silk',
    'PROFILE': 'outline'
}

STANDARD_COLOR_SET = {
    'drill',
    'outline',
    'top_copper',
    'top_mask',
    'top_silk',
    'bottom_copper',
    'bottom_mask',
    'bottom_silk',
}


class Board:
    def __init__(self, filepath):
        self.files = {}
        extension = os.path.splitext(filepath)[1].lower()
        if extension == 'zip':
            temp_path = tempfile.mkdtemp()
            logging.info(f'Extracting files to {temp_path}')
            with zipfile.ZipFile(file, 'r') as zipped:
                zipped.extractall(temp_path)
                self.read_files_in_folder(temp_path)
        elif os.path.isdir(self.path):
            self.read_files_in_folder(filepath)
        else:
            raise ValueError(f"Unknown file: {filepath}")


    def read_in_files_from_folder(self, path):
        for root, dirs, files in os.walk(path):
            for filename in files:
                extension = os.path.splitext(filename)[1].upper()
                if extension in FILE_EXT_TO_NAME:
                    self.files[FILE_EXT_TO_NAME[extension]] = filename
                    else:
                        logging.info(f"Unknown file type: {filename}")
