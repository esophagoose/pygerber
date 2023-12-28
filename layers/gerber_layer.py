import copy
import enum
import logging
import os
import re
import typing
from typing import List, Tuple

import layers.aperture as aperture_lib
import standard.gerber as gf


class Units(enum.Enum):
    MM = "MM"
    INCH = "IN"
    UNKNOWN = "XX"


class OperationState(typing.NamedTuple):
    aperture: aperture_lib.Aperture
    interpolation: gf.GerberFormat
    point: tuple
    previous_point: tuple
    polarity: bool
    quadrant_mode: gf.GerberFormat
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

        self._in_header = True
        self.header = []
        self.current_aperture = None
        self.interpolation = None
        self.attributes = {}
        self.region = False
        self.polarity = None
        self.path = filepath
        self.apertures = {}
        self.current_point = None
        self.comments = []
        self.units = Units.UNKNOWN
        self.quadrant_mode = None
        self.scalars = ()
        self.decimal_digits = (0, 0)
        self.integer_digits = (0, 0)
        self.operations: List[Tuple[gf.GerberFormat, OperationState]] = []
        self._regions = []
        self.aperture_factory = aperture_lib.ApertureFactory()
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
            if self._in_header:
                self.header.append(content)
            else:
                self.comments.append(content)
        elif op_type == gf.GerberFormat.UNITS:
            self._in_header = False
            self.units = Units(data[2:])
            logging.info(f"Switching units to {self.units}")
        elif op_type in [
            gf.GerberFormat.DEPRECATED_UNITS_MM,
            gf.GerberFormat.DEPRECATED_UNITS_INCH,
        ]:
            u = "MM" if op_type == gf.GerberFormat.DEPRECATED_UNITS_MM else "INCH"
            self.units = Units(u)
            logging.info(f"Switching units to {self.units}")
        elif op_type in [
            gf.GerberFormat.QUADMODE_SINGLE,
            gf.GerberFormat.QUADMODE_MULTI,
        ]:
            logging.info(f"Switching quadrant mode to: {op_type}")
            self.quadrant_mode = op_type
        elif op_type == gf.GerberFormat.FORMAT:
            self._set_scalars(data)
            logging.info(f"Got decimal places: {self.scalars}")
        elif op_type == gf.GerberFormat.LOAD_POLARITY:
            self.polarity = content == "D"
            logging.info(f"Setting polarity to {self.polarity}")
        elif op_type == gf.GerberFormat.APERTURE_DEFINE:
            aperture = self.aperture_factory.from_aperture_define(
                content, copy.deepcopy(self.comments)
            )
            self.apertures[aperture.index] = aperture
            self.comments.clear()
            logging.info(f"Add aperture: {aperture.index}")
        elif op_type == gf.GerberFormat.APERTURE_MACRO:
            self.aperture_factory.define_macro(content)
            logging.info(f"Processed aperture macro: {content}")
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
            op = self._run_operation(content)
            logging.info(f"Operation: {op_type}, point: {self.current_point}")
            self.current_point = op.point
            if self.region:
                self._regions.append((op_type, op))
            else:
                self.operations.append((op_type, op))
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

    def point_to_text(self, point):
        assert point[0] < pow(10, self.integer_digits.x), "Overflow x value"
        assert point[1] < pow(10, self.integer_digits.y), "Overflow y value"
        x = int(point[0] * pow(10, self.decimal_digits.x))
        y = int(point[1] * pow(10, self.decimal_digits.y))
        return f"X{x}Y{y}"

    def write(self, filename):
        def write_line(message: str, _file, grouped=False):
            message += "*"
            if grouped:
                message = f"%{message}%"
            _file.write(message + "\n")

        state = self.operations[0][1]
        with open(filename, "w") as f:
            current_aperture = None
            for comment in self.header:
                write_line(gf.GerberFormat.COMMENT.value + comment, f)
            write_line(gf.GerberFormat.UNITS.value + state.units.value, f, True)
            format_spec = gf.Point(
                x=(self.integer_digits.x * 10 + self.decimal_digits.x),
                y=(self.integer_digits.y * 10 + self.decimal_digits.y),
            )

            write_line("FSLA" + format_spec.to_text(), f, True)
            write_line(state.quadrant_mode.value, f)
            for macro in self.aperture_factory.macros.values():
                write_line(self.aperture_factory.macro_to_str(macro), f)
            for aperture in self.apertures.values():
                for comment in aperture.comments:
                    write_line(gf.GerberFormat.COMMENT.value + comment, f)
                statement = self.aperture_factory.to_aperture_define(aperture)
                write_line(statement, f, True)
            # import code

            # code.interact(local=locals())
            polarity = gf.GerberFormat.LOAD_POLARITY.value
            polarity += "D" if state.polarity else "C"
            write_line(polarity, f, True)
            # return OperationState(
            #     aperture=aperture if not self.region else None,
            #     polarity=self.polarity,
            #     units=self.units,
            #     quadrant_mode=self.quadrant_mode,
            #     scalars=self.scalars,
            #     interpolation=self.interpolation,
            #     previous_point=self.current_point,
            #     point=point,
            # )
            for op_type, op in self.operations:
                if op.aperture and op.aperture != current_aperture:
                    write_line(f"D{op.aperture.index}", f)
                    current_aperture = op.aperture
                write_line(self.point_to_text(op.point) + op_type.value, f)
            write_line(gf.GerberFormat.END_OF_FILE.value, f)

    def scale(self, point):
        x = round(point[0] * self.scalars[0], self.decimal_digits.x)
        y = round(point[1] * self.scalars[1], self.decimal_digits.y)
        return x, y

    def _run_operation(self, content: str):
        values = re.findall(r"[A-Z]([\+|-]*\d+)", content)
        assert len(values) in [2, 4], f"Invalid operation parsing: {content}"
        assert self.region or self.current_aperture, "Invalid operation: no aperture!"

        point = self.scale((float(values[0]), float(values[1])))
        if len(values) == 4:
            x, y, i, j = values
            point = self.scale((float(x), float(y))), self.scale((float(i), float(j)))
        aperture = self.apertures[self.current_aperture]
        return OperationState(
            aperture=aperture if not self.region else None,
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
        intx, decx, inty, decy = match.groups()
        self.scalars = (pow(10, -int(decx)), pow(10, -int(decy)))
        self.integer_digits = gf.Point(int(intx), int(inty))
        self.decimal_digits = gf.Point(int(decx), int(decy))
