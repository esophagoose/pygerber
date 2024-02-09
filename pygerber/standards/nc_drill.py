from enum import Enum

FILE_EXTENSIONS = ["DRL", "XLN"]


class NCDrillFormat(Enum):
    COMMENT = ";"
    START_OF_HEADER = "M48"
    FORMAT = "FMAT,2"
    SET_UNIT_MM = "METRIC"
    SET_UNIT_INCH = "INCH"
    END_OF_HEADER = "%"
    DRILL_MODE = "G05"
    ROUT_MODE = "G00"
    ABSOLUTE_UNITS = "G90"
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
        try:
            return NCDrillFormat(command), ""
        except ValueError:
            pass
        if command[0] == "G0":
            return NCDrillFormat(command[:3]), command[3:]
        for cmd in NCDrillFormat:
            if command.startswith(cmd.value):
                return cmd, command
        raise ValueError(f"Invalid drill command: {command}")
