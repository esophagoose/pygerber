import enum


class GerberFormat(enum.Enum):
    FORMAT = "FS"  # coordinate format
    UNITS = "MO"  # sets the units
    APERTURE_DEFINE = "AD"  # Defines a template-based aperture
    APERTURE_MACRO = "AM"  # Defines a macro aperture template
    APERTURE_BLOCK = "AB"  # Defines a block aperture
    SET_APERATURE = "DXX"  # (XX > 10) sets the current aperture
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

    @classmethod
    def lookup(cls, command):
        # Two styles of commands: [A-Z][A-Z] and [A-Z][0-9][0-9]
        if command[1].isalpha():
            return GerberFormat(command[:2]), command[2:]
        elif command[0] == "D":
            return GerberFormat.SET_APERATURE, command[3:]
        elif command[0] == "X" and command[-3] == "D":
            return GerberFormat(command[-3:]), command[:-3]
        else:
            return GerberFormat(command[:3]), command[3:]
