from enum import Enum
import logging
import re
import os

import coloredlogs

coloredlogs.DEFAULT_LOG_FORMAT = "GerberLayer: %(asctime)s %(levelname)s %(message)s"
coloredlogs.install(level="WARNING", format="GerberLayer: %(message)s")

class DrillCommands(Enum):
    COMMENT = ";"
    START_OF_HEADER = "M48"
    SET_UNIT_MM = "METRIC"
    SET_UNIT_INCH = "INCH"
    TOOL_COMMAND= "T"
    END_OF_HEADER = "%"
    DRILL_MODE = "G05"
    ROUT_MODE = "G00"
    SELECT_TOOL = "T"
    DRILL_HIT = "X"
    TOOL_DOWN = "M15"
    TOOL_UP = "M16"
    LINEAR_ROUT = "G01"
    CIRCULAR_CLOCKWISE_ROUT = "G02"
    CIRCULAR_COUNTERCLOCKWISE_ROUT = "G03"
    END_OF_FILE = "M30"

    @classmethod
    def lookup(cls, command):
        # Two styles of commands: [A-Z][A-Z] and [A-Z][0-9][0-9]
        try:
            return DrillCommands(command), ""
        except ValueError:
            pass
        if command[0] == "G0":
            return DrillCommands(command[:3]), command[3:]
        for cmd in DrillCommands:
            if command.startswith(cmd.value):
                return cmd, command
        raise ValueError(f"Invalid drill command: {command}")

def parse_xy(text):
    match = re.search(r"X([\+|\d.]+)Y([\+|\d.]+)", text)
    if match:
        x, y = match.groups()
        return float(x), float(y)
    else:
        raise ValueError(f"Invalid XY format: {text}")
    

class NCDrill:
    def __init__(self, filepath):
        logging.info(f"Starting drill layer importer:")
        logging.info(f"\tFile: {filepath}")

        self.filename = os.path.basename(filepath)
        self.path = filepath
        self.tools = {}
        self.mode = DrillCommands.DRILL_MODE
        self.operations = []
        self.comments = ""
        self._selected_tool = None
        self._rout = []
        self._routing = False

    def read(self):
        in_header = True
        with open(self.path, "r") as f:
            for index, line in enumerate(f.readlines()):
                line = line.strip()
                if not line:
                    continue
                logging.debug(f"Line: {index}, Processing: {line}")
                if line == DrillCommands.START_OF_HEADER.value:
                    in_header = True
                    continue
                if line == DrillCommands.END_OF_HEADER.value:
                    in_header = False
                    continue
                if in_header:
                    self._process_header(line)
                else:
                    self._process_content(line)
        return self.operations

    def _process_header(self, data):
        op_type, content = DrillCommands.lookup(data)

        if op_type == DrillCommands.COMMENT:
            self.comments += content
        elif op_type in [DrillCommands.SET_UNIT_MM, DrillCommands.SET_UNIT_INCH]:
            self.units = op_type.value
        elif op_type == DrillCommands.TOOL_COMMAND:  # tool declaration
            index, diameter = re.search(r"T(\d+)C([\d.]+)", data).groups()
            self.tools[int(index)] = float(diameter)
        else:
            raise ValueError(f"Unknown command: {op_type}")

    def _process_content(self, data):
        op_type, content = DrillCommands.lookup(data)

        if op_type == DrillCommands.COMMENT:
            self.comments += content
        elif op_type in [DrillCommands.DRILL_MODE,DrillCommands.ROUT_MODE]:
            self.mode = op_type
        elif op_type == DrillCommands.TOOL_COMMAND:
            # handle tool selection
            index = int(content[1:])
            self._selected_tool = self.tools[index]
        elif op_type == DrillCommands.DRILL_HIT:
            assert self.mode == DrillCommands.DRILL_MODE, "Must be in drill mode to hit"
            point = parse_xy(content)
            self.operations.append((self.mode, self._selected_tool, point))
        elif op_type == DrillCommands.TOOL_DOWN:
            self._routing = True
        elif op_type == DrillCommands.TOOL_UP:
            self.operations.append((self.mode, self._selected_tool, self._rout))
            self._rout.clear()
            self._routing = False
        elif op_type == DrillCommands.LINEAR_ROUT:
            assert self._routing, f"Invalid {op_type} while tool is up"
            self._rout.append((op_type, parse_xy(content)))
        elif op_type == DrillCommands.CIRCULAR_CLOCKWISE_ROUT:
            assert self._routing, f"Invalid {op_type} while tool is up"
            self._rout.append((op_type, parse_xy(content)))
        elif op_type == DrillCommands.CIRCULAR_COUNTERCLOCKWISE_ROUT:
            assert self._routing, f"Invalid {op_type} while tool is up"
            self._rout.append((op_type, parse_xy(content)))
        elif op_type == DrillCommands.END_OF_FILE:
            return
        else:
            raise ValueError(f"Unknown command: {op_type}")


if __name__ == "__main__":
    NCDrill("./testdata/Gerber_Drill_PTH.DRL").read()
