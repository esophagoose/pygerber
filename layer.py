import os
import re
import enum
import logging

from format import GerberFormat

import coloredlogs

coloredlogs.DEFAULT_LOG_FORMAT = "GerberLayer: %(asctime)s %(levelname)s %(message)s"
coloredlogs.install(level="INFO", format="GerberLayer: %(message)s")

FILE_EXT_TO_NAME = {
    ".drl": "drill",
    ".xln": "drill",
    ".gko": "outline",
    ".gm1": "outline",
    ".gtl": "top_copper",
    ".gts": "top_mask",
    ".gto": "top_silk",
    ".gbl": "bottom_copper",
    ".gbs": "bottom_mask",
    ".gbo": "bottom_silk",
    ".profile": "outline",
}


class Unit(enum.Enum):
    MM = "MM"
    INCH = "IN"
    UNKNOWN = "XX"


class QuadrantMode(enum.Enum):
    SINGLE = 1
    MULTI = 2
    UNKNOWN = 3


REGEX_OPERATION_CMD = r"^X(\d+)Y(\d+)$"


def get_xy_point(text):
    x, y = re.search(REGEX_OPERATION_CMD, text).groups()
    return (float(x), float(y))


class Layer:
    def __init__(self, filepath):
        extension = os.path.splitext(filepath)[1].lower()
        if extension not in FILE_EXT_TO_NAME:
            raise ValueError(f"Unknown file: {filepath}")

        logging.info(f"Starting gerber layer importer:")
        logging.info(f"\tFile: {filepath}")
        logging.info(f"\tType: {FILE_EXT_TO_NAME[extension].upper()}")

        self.current_aperature = None
        self.polarity = None
        self.path = filepath

    def read(self):
        multiline = False
        with open(self.path, "r") as f:
            buffer = ""
            for line in f.readlines():
                buffer += line
                if ";" in line:
                    line = line[: line.index(";")]
                    logging.debug(f"Stripped comment: '{line[line.index(';'):]}'")
                if line.count("%") not in [0, 2]:
                    multiline = not multiline
                if multiline:
                    continue
                buffer = buffer.strip()
                if buffer.startswith("%") and buffer.endswith("%"):
                    buffer = buffer[1:-1]
                if buffer.endswith("*"):
                    buffer = buffer[:-1]
                self._process(buffer)
                buffer = ""
        return self

    def _process(self, data):
        aperatures = {}
        comments = ""
        unit = Unit.UNKNOWN
        quadrant_mode = QuadrantMode.UNKNOWN
        decimal = ()
        self.polarity = True
        _type, content = GerberFormat.lookup(data)

        if _type == GerberFormat.COMMENT:
            comments += data[4:]
        elif _type == GerberFormat.UNITS:
            unit = Unit(data[2:])
            logging.info(f"Switching units to {unit}")
        elif _type == GerberFormat.QUADMODE_SINGLE:
            logging.info("Switching to single quadrant mode")
            quadrant_mode = QuadrantMode.SINGLE
        elif _type == GerberFormat.QUADMODE_MULTI:
            logging.info("Switching to multi quadrant mode")
            quadrant_mode = QuadrantMode.MULTI
        elif _type == GerberFormat.FORMAT:
            decimal = self.get_decimal_places(data)
            logging.info(f"Got decimal places: {decimal}")
        elif _type == GerberFormat.LOAD_POLARITY:
            self.polarity = content == "D"
            logging.info(f"Setting polarity to {self.polarity}")
        elif _type == GerberFormat.APERTURE_DEFINE:
            aid, shape, dimensions = self._define_aperature(content)
            aperatures[aid] = (shape, dimensions)
            logging.info(f"Add aperature: {aid}")
        elif _type == GerberFormat.SET_APERATURE:
            self.current_aperature = int(data[1:])
            logging.info(f"Changing current aperature to: {self.current_aperature}")
        elif _type == GerberFormat.OPERATION_INTERP:
            point = get_xy_point(content)
            self.make_line(self.current_point, point)
            self.current_point = point
            logging.info(f"Draw line from {self.current_point} to {point}")
        elif _type == GerberFormat.OPERATION_MOVE:
            self.current_point = get_xy_point(content)
            logging.info(f"Moved point to {self.current_point}")
        elif _type == GerberFormat.OPERATION_FLASH:
            point = get_xy_point(content)
            self.add_aperature(point)
            self.current_point = point
            logging.info(f"Flash aperture to {self.current_point}")
        elif _type == GerberFormat.APERTURE_MACRO:
            logging.warning("Unhandled aperture define")
        elif _type == GerberFormat.END_OF_FILE:
            logging.info("End of file command.")
        else:
            logging.warning(f"Unknown line: {data}")

    def add_aperature(self, point, aperature=None):
        if not aperature:
            aperature = self.current_aperature
        raise NotImplementedError()

    def _define_aperature(self, line):
        pattern = re.compile(r"^D(\d+)([A-z]+),([\d.X]+)$")
        matches = pattern.findall(line)
        if len(matches) != 1:
            raise RuntimeError(f"Failed to match one item! {matches} {line}")
        aperture_id, shape, dimensions = matches[0]
        return aperture_id, shape, dimensions.split("X")
