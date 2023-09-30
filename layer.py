import os
import re
import enum
import logging
import typing
import gerber_format as gf

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


class Units(enum.Enum):
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


class OperationState(typing.NamedTuple):
    aperatures: dict
    current_aperature: int
    current_point: tuple
    scalars: tuple
    polarity: bool
    quadrant_mode: QuadrantMode
    units: Units


class GerberLayer:
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
        self.aperatures = {}
        self.current_point = None
        self.comments = ""
        self.units = Units.UNKNOWN
        self.quadrant_mode = QuadrantMode.UNKNOWN
        self.scalars = ()
        self.sigfig_x = 1
        self.sigfig_y = 1
        self.operations = []

    def read(self):
        multiline = False
        with open(self.path, "r") as f:
            buffer = ""
            for line in f.readlines():
                buffer += line
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
        return self.operations

    def _process(self, data):
        op_type, content = gf.GerberFormat.lookup(data)

        if op_type == gf.GerberFormat.COMMENT:
            self.comments += content + "\n"
        elif op_type == gf.GerberFormat.UNITS:
            self.units = Units(data[2:])
            logging.info(f"Switching units to {self.units}")
        elif op_type == gf.GerberFormat.QUADMODE_SINGLE:
            logging.info("Switching to single quadrant mode")
            self.quadrant_mode = QuadrantMode.SINGLE
        elif op_type == gf.GerberFormat.QUADMODE_MULTI:
            logging.info("Switching to multi quadrant mode")
            self.quadrant_mode = QuadrantMode.MULTI
        elif op_type == gf.GerberFormat.FORMAT:
            self._set_scalars(data)
            logging.info(f"Got decimal places: {self.scalars}")
        elif op_type == gf.GerberFormat.LOAD_POLARITY:
            self.polarity = content == "D"
            logging.info(f"Setting polarity to {self.polarity}")
        elif op_type == gf.GerberFormat.APERTURE_DEFINE:
            aid, shape, dimensions = self._define_aperature(content)
            self.aperatures[aid] = (shape, dimensions)
            logging.info(f"Add aperature: {aid}")
        elif op_type == gf.GerberFormat.SET_APERATURE:
            self.current_aperature = int(data[1:])
            logging.info(f"Current aperature set to: {self.current_aperature}")
        elif op_type in [
            gf.GerberFormat.OPERATION_FLASH,
            gf.GerberFormat.OPERATION_MOVE,
            gf.GerberFormat.OPERATION_INTERP,
        ]:
            self._run_operation(op_type, content)
            logging.info(f"Operation: {op_type}, point: {self.current_point}")
        elif op_type == gf.GerberFormat.APERTURE_MACRO:
            logging.warning("Unhandled aperture define")
        elif op_type == gf.GerberFormat.END_OF_FILE:
            logging.info("End of file command.")
        else:
            logging.warning(f"Unknown line: {data}")

    def scale(self, point):
        x = round(point[0] * self.scalars[0], self.sigfig_x)
        y = round(point[1] * self.scalars[1], self.sigfig_y)
        return x, y

    def save_state(self):
        return OperationState(
            aperatures=self.aperatures,
            current_aperature=self.current_aperature,
            polarity=self.polarity,
            units=self.units,
            quadrant_mode=self.quadrant_mode,
            scalars=self.scalars,
            current_point=self.current_point,
        )

    def _define_aperature(self, line):
        pattern = re.compile(r"^D(\d+)([A-z]+),([\d.X]+)$")
        matches = pattern.findall(line)
        if len(matches) != 1:
            raise RuntimeError(f"Failed to match one item! {matches} {line}")
        aperture_id, shape, dimensions = matches[0]
        return aperture_id, shape, dimensions.split("X")

    def _run_operation(self, op_type: gf.GerberFormat, content: str):
        point = self.scale(get_xy_point(content))
        self.operations.append((op_type, point, self.save_state()))
        self.current_point = point

    def _set_scalars(self, text):
        regex = r"FSLAX(\d)(\d)Y(\d)(\d)"
        match = re.search(regex, text)
        if not match:
            raise RuntimeError("No decimal places available!")
        intx, decx, inty, decy = match.groups()
        self.scalars = (pow(10, -int(decx)), pow(10, -int(decy)))
        self.sigfig_x = int(decx)
        self.sigfig_y = int(decy)


GerberLayer("./outputs/gerber_writer_example_synthetic.gtl").read()
