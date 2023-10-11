import copy
import enum
import logging
import os
import re
import typing

import standard.gerber as gf


class Units(enum.Enum):
    MM = "MM"
    INCH = "IN"
    UNKNOWN = "XX"


class QuadrantMode(enum.Enum):
    SINGLE = 1
    MULTI = 2
    UNKNOWN = 3


class ApertureTemplate(enum.Enum):
    CIRCLE = "C"
    RECT = "R"
    OBROUND = "O"
    POLYGON = "P"
    CUSTOM = "X"

    @classmethod
    def get(cls, value):
        if len(value) == 1:
            return ApertureTemplate(value)
        return ApertureTemplate.CUSTOM


class Aperture(typing.NamedTuple):
    index: int
    type: ApertureTemplate
    dimension: tuple


class OperationState(typing.NamedTuple):
    aperture: Aperture
    interpolation: gf.GerberFormat
    point: tuple
    previous_point: tuple
    polarity: bool
    quadrant_mode: QuadrantMode
    scalars: tuple
    units: Units


class GerberLayer:
    def __init__(self, filepath):
        filename, ext = os.path.splitext(filepath)
        self.filename = os.path.basename(filename)
        extension = ext.lower()
        if extension not in gf.FILE_EXT_TO_NAME:
            raise ValueError(f"Unknown file: {filepath}")
        self.file_type = gf.FILE_EXT_TO_NAME[extension]

        logging.info(f"Starting gerber layer importer:")
        logging.info(f"\tFile: {filepath}")
        logging.info(f"\tType: {self.file_type.upper()}")

        self.current_aperture = None
        self.interpolation = None
        self.attributes = {}
        self.region = False
        self.polarity = None
        self.path = filepath
        self.apertures = {}
        self.current_point = None
        self.comments = ""
        self.units = Units.UNKNOWN
        self.quadrant_mode = QuadrantMode.UNKNOWN
        self.scalars = ()
        self.sigfig_x = 1
        self.sigfig_y = 1
        self.operations = []
        self._regions = []
        self.collection_of_region = []

    def read(self, raise_on_unknown_command=False):
        multiline = False
        with open(self.path, "r") as f:
            buffer = ""
            for index, line in enumerate(f.readlines()):
                if not line.strip():
                    continue
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
                logging.debug(f"Line: {index}, Processing: {buffer}")
                self._process(buffer, raise_on_unknown_command)
                buffer = ""
        return self.operations, self.collection_of_region

    def _process(self, data, raise_on_unknown_command):
        op_type, content = gf.GerberFormat.lookup(data)

        if op_type in [
            gf.GerberFormat.INTERP_MODE_LINEAR,
            gf.GerberFormat.INTERP_MODE_CW,
            gf.GerberFormat.INTERP_MODE_CCW,
        ]:
            self.interpolation = op_type
            if content:  # this is rare and poor syntax
                self._process(content, raise_on_unknown_command)
        elif op_type == gf.GerberFormat.COMMENT:
            self.comments += content + "\n"
        elif op_type == gf.GerberFormat.UNITS:
            self.units = Units(data[2:])
            logging.info(f"Switching units to {self.units}")
        elif op_type in [
            gf.GerberFormat.DEPRECATED_UNITS_MM,
            gf.GerberFormat.DEPRECATED_UNITS_INCH,
        ]:
            u = "MM" if op_type == gf.GerberFormat.DEPRECATED_UNITS_MM else "INCH"
            self.units = Units(u)
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
            aperture = self._define_aperture(content)
            self.apertures[aperture.index] = aperture
            logging.info(f"Add aperture: {aperture.index}")
        elif op_type == gf.GerberFormat.SET_APERTURE:
            self.current_aperture = int(data[1:])
            logging.info(f"Current aperture set to: {self.current_aperture}")
        elif op_type == gf.GerberFormat.ATTRIBUTE_FILE:
            params = content.split(",")
            self.attributes[params[0][1:]] = params[1:]
        elif op_type in [
            gf.GerberFormat.ATTRIBUTE_OBJECT,
            gf.GerberFormat.ATTRIBUTE_DELETE,
            gf.GerberFormat.ATTRIBUTE_APERTURE,
        ]:
            pass  # TODO: no-op for now - these are just comments
        elif op_type in [
            gf.GerberFormat.OPERATION_FLASH,
            gf.GerberFormat.OPERATION_MOVE,
            gf.GerberFormat.OPERATION_INTERP,
        ]:
            op = self._run_operation(op_type, content)
            logging.info(f"Operation: {op_type}, point: {self.current_point}")
            self.current_point = op.point
            if self.region:
                self._regions.append((op_type, op))
            else:
                self.operations.append((op_type, op))
        elif op_type == gf.GerberFormat.APERTURE_MACRO:
            logging.warning("Unhandled aperture define")
        elif op_type in [gf.GerberFormat.REGION_START, gf.GerberFormat.REGION_END]:
            self.region = op_type == gf.GerberFormat.REGION_START
            if not self.region:
                region = copy.deepcopy(self._regions)
                self.collection_of_region.append(region)
                self._regions.clear()
            logging.info(f"{'START' if self.region else 'END'} Region")
        elif op_type in [gf.GerberFormat.DEPRECATED_SELECT_APERTURE]:
            self._process(content, raise_on_unknown_command)  # no-op
        elif op_type in [gf.GerberFormat.DEPRECATED_PROGRAM_STOP]:
            pass  # no-op
        elif op_type == gf.GerberFormat.END_OF_FILE:
            logging.info("End of file command.")
        else:
            logging.warning(f"Unknown command: {data}")
            if raise_on_unknown_command:
                raise ValueError(f"Unknown command: {data}")

    def scale(self, point):
        x = round(point[0] * self.scalars[0], self.sigfig_x)
        y = round(point[1] * self.scalars[1], self.sigfig_y)
        return x, y

    def _define_aperture(self, line):
        pattern = re.compile(r"^D(\d+)([A-z]+),([\d.X]+)$")
        aperture_id, shape, dimensions = pattern.findall(line)[0]
        return Aperture(
            index=int(aperture_id),
            type=ApertureTemplate.get(shape),
            dimension=[float(d) for d in dimensions.split("X")],
        )

    def _run_operation(self, op_type: gf.GerberFormat, content: str):
        values = re.findall(r"[A-Z]([\+|-]*\d+)", content)
        assert len(values) in [2, 4], f"Invalid operation parsing: {content}"
        assert self.region or self.current_aperture, "Invalid operation: no aperture!"

        point = self.scale((float(values[0]), float(values[1])))
        if len(values) == 4:
            x, y, i, j = values
            point = self.scale((float(x), float(y))), self.scale(
                (float(i), float(j)))
        aperture = None if self.region else self.apertures[self.current_aperture]
        return OperationState(
            aperture=aperture,
            polarity=self.polarity,
            units=self.units,
            quadrant_mode=self.quadrant_mode,
            scalars=self.scalars,
            interpolation=self.interpolation,
            previous_point=self.current_point,
            point=point,
        )

    def _set_scalars(self, text):
        regex = r"FSLAX(\d)(\d)Y(\d)(\d)"
        match = re.search(regex, text)
        if not match:
            raise RuntimeError("No decimal places available!")
        _, decx, _, decy = match.groups()
        self.scalars = (pow(10, -int(decx)), pow(10, -int(decy)))
        self.sigfig_x = int(decx)
        self.sigfig_y = int(decy)
