import enum


FILE_EXT_TO_NAME = {
    ".gbr": "generic",
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


class GerberFormat(enum.Enum):
    FORMAT = "FS"  # coordinate format
    UNITS = "MO"  # sets the units
    APERTURE_DEFINE = "AD"  # Defines a template-based aperture
    APERTURE_MACRO = "AM"  # Defines a macro aperture template
    APERTURE_BLOCK = "AB"  # Defines a block aperture
    SET_APERTURE = "DXX"  # (XX > 10) sets the current aperture
    OPERATION_INTERP = "D01"  # Draws using the current aperture
    OPERATION_MOVE = "D02"  # Moves the current point to command
    OPERATION_FLASH = "D03"  # Creates a flash object using the current aperture
    INTERP_MODE_LINEAR = "G01"  # interpolation mode to linear
    INTERP_MODE_CW = "G02"  # interpolation mode to clockwise circular
    INTERP_MODE_CCW = "G03"  # interpolation mode to counterclockwise circular
    QUADMODE_SINGLE = "G74"  # Sets quadrant mode to single quadrant
    QUADMODE_MULTI = "G75"  # Sets quadrant mode to multi quadrant
    LOAD_POLARITY = "LP"  # Loads the polarity object transformation parameter
    LOAD_MIRRORING = "LM"  # Loads the mirror object transformation parameter
    LOAD_ROTATION = "LR"  # Loads the rotation object transformation parameter
    LOAD_SCALING = "LS"  # Loads the scale object transformation parameter
    REGION_START = "G36"  # Starts a region
    REGION_END = "G37"  # Ends the region
    STEP_AND_REPEAT = "SR"  # Open or closes a step and repeat statement
    COMMENT = "G04"  # Comment
    ATTRIBUTE_FILE = "TF"  # Set a file attribute
    ATTRIBUTE_APERTURE = "TA"  # Adds an aperture attribute
    ATTRIBUTE_OBJECT = "TO"  # Adds an object attribute
    ATTRIBUTE_DELETE = "TD"  # Deletes attributes
    END_OF_FILE = "M02"
    # Deprecated commands
    DEPRECATED_UNITS_INCH = "G70"  # set units to inches - Use MO
    DEPRECATED_UNITS_MM = "G71"  # set units to mm - Use MO
    DEPRECATED_ABSOLUTE_NOTATION = "G90"  # Use FS
    DEPRECATED_INCREMENTAL_NOTATION = "G91"  # Use FS
    DEPRECATED_SELECT_APERTURE = "G54"  # No-op - before aperture selection
    DEPRECATED_PROGRAM_STOP = "M00"  # Same as M02
    DEPRECATED_OPTIONAL_STOP = "M01"  # No-op
    DEPRECATED_IMAGE_POLARITY = "IP"
    DEPRECATED_AXES_CORRESPONDENCE = "AS"
    DEPRECATED_IMAGE_ROTATION = "IR"
    DEPRECATED_IMAGE_MIRRORING = "MI"
    DEPRECATED_IMAGE_OFFSET = "OF"
    DEPRECATED_SCALE_FACTOR = "SF"
    DEPRECATED_FILE_IMAGE_NAME = "IN"  # No-op, type of comment. Use G04
    DEPRECATED_LOAD_NAME = "LN"  # No-op, type of comment. Use G04

    @classmethod
    def lookup(cls, command):
        # Two styles of commands: [A-Z][A-Z] and [A-Z][0-9][0-9]
        if command[1].isalpha():
            return GerberFormat(command[:2]), command[2:]
        elif command[0] == "D":
            return GerberFormat.SET_APERTURE, command[3:]
        elif command[0] == "X" and command[-3] == "D":
            return GerberFormat(command[-3:]), command[:-3]
        else:
            return GerberFormat(command[:3]), command[3:]
