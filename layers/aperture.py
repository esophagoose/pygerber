import typing
import enum
import re
import logging
import math


class ApertureCircle(typing.NamedTuple):
    diameter: float
    cx: float = 0
    cy: float = 0

    @property
    def r(self):
        return self.diameter / 2


class ApertureRectangle(typing.NamedTuple):
    width: float
    height: float
    cx: float = 0
    cy: float = 0
    rotation: float = 0


class ApertureObround(typing.NamedTuple):
    width: float
    height: float
    cx: float = 0
    cy: float = 0


class AperturePolygon(typing.NamedTuple):
    diameter: float
    vertices: int
    rotation: float = 0
    cx: float = 0
    cy: float = 0


class ApertureOutline(typing.NamedTuple):
    points: typing.Tuple[int]
    rotation: float = 0


class MacroPrimitive(enum.Enum):
    COMMENT = 0
    CIRCLE = 1
    VECTOR_LINE = 20
    CENTER_LINE = 21
    OUTLINE = 4
    POLYGON = 5
    MOIRE = 6
    THERMAL = 7


class Aperture(typing.NamedTuple):
    index: str
    exposure: bool
    shape: typing.Any
    rotation: float = 0
    hole: float = 0


class Macro(typing.NamedTuple):
    statements: typing.List[tuple[MacroPrimitive, str]]

    def validate_values(self, values):
        data = [text for _, text in self.statements]
        results = re.findall(r"\$(\d+)", " ".join(data))
        count = len(set(results))
        error = f"Invalid values! Got {len(values)}, expected {count}"
        assert count == len(values), error

    def _parse(self, values: typing.List[float]):
        parsed = []
        for p, statement in self.statements:
            for i, value in enumerate(values):
                statement = statement.replace(f"${i + 1}", str(value))
            parsed.append((p, [float(v) for v in statement.split(",")]))
        return parsed

    def generate_aperture(self, index: int, values: typing.List[float]):
        self.validate_values(values)
        shape = None
        exposure = True
        rotation = 0
        for primitive, statement in self._parse(values):
            if primitive == MacroPrimitive.CIRCLE:
                exposure, diameter, cx, cy, _ = statement
                shape = ApertureCircle(
                    diameter=diameter,
                    cx=cx,
                    cy=cy,
                )
            elif primitive == MacroPrimitive.VECTOR_LINE:
                exposure, h, x1, y1, x2, y2, rotation = statement
                width = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                angle = math.atan2(y2 - y1, x2 - x1)
                shape = ApertureRectangle(
                    width=width,
                    height=h,
                    cx=x1 + (x2 - x1) / 2,
                    cy=y1 + (y2 - y1) / 2,
                    rotation=angle,
                )
            elif primitive == MacroPrimitive.CENTER_LINE:
                exposure, w, h, cx, cy, rotation = statement
                shape = ApertureRectangle(
                    width=w,
                    height=h,
                    cx=cx,
                    cy=cy,
                )
            elif primitive == MacroPrimitive.OUTLINE:
                exposure = bool(statement[0])
                verticies = statement[1] + 1  # initial point isn't counted
                rotation = statement[-1]
                points = statement[2:-1]
                assert len(points) == 2 * verticies, "Malformed command"
                shape = ApertureOutline(points=points, rotation=rotation)
            elif primitive == MacroPrimitive.POLYGON:
                exposure, verticies, cx, cy, d, rotation = statement
                shape = AperturePolygon(
                    diameter=d,
                    vertices=int(verticies),
                    cx=cx,
                    cy=cy,
                )
            elif primitive == MacroPrimitive.MOIRE:
                cx, cy, d, rh, gap, rings, xw, xl, rotation = statement
                raise NotImplementedError(MacroPrimitive.MOIRE)
            elif primitive == MacroPrimitive.THERMAL:
                cx, cy, od, id, gap, rotation = statement
                raise NotImplementedError(MacroPrimitive.THERMAL)
            else:
                raise NotImplementedError(statement)
        return Aperture(
            index=index, exposure=exposure, shape=shape, rotation=rotation, hole=0
        )


class ApertureFactory:
    def __init__(self):
        self.macros: typing.Dict[str, Macro] = {}

    def from_aperture_define(self, statement):
        def pad_optional_params(params: typing.List[float], count: int):
            return params + [0] * (count - len(params))

        pattern = re.compile(r"^D(\d+)([A-z]+),([\d.X]+)$")
        aperture_id, shape, params = pattern.findall(statement)[0]
        parameters = [float(p) for p in params.split("X")]
        hole = 0
        if shape in self.macros:
            macro = self.macros[shape]
            return macro.generate_aperture(int(aperture_id), parameters)
        elif shape == "C":
            diameter, hole = pad_optional_params(parameters, 2)
            shape = ApertureCircle(diameter=diameter)
        elif shape == "R":
            width, height, hole = pad_optional_params(parameters, 3)
            shape = ApertureRectangle(width=width, height=height)
        elif shape == "O":
            width, height, hole = pad_optional_params(parameters, 3)
            shape = ApertureObround(width=width, height=height)
        elif shape == "P":
            d, verticies, rot, hole = pad_optional_params(parameters, 4)
            shape = AperturePolygon(diameter=d, verticies=verticies, rotation=rot)
        else:
            raise ValueError(f"Invalid aperture shape: {statement}")
        return Aperture(
            index=int(aperture_id), exposure=True, shape=shape, rotation=0, hole=hole
        )

    def define_macro(self, statement):
        data = statement.split("*\n")
        name, rows = data[0], data[1:]
        statements = []
        for row in rows:
            if not row:
                continue
            row = row.replace("\n", "")
            primitive = MacroPrimitive(int(row[0]))
            if primitive == MacroPrimitive.COMMENT:
                logging.info(f"Macro {name} comment: {row[1:]}")
                continue
            assert row[1] == ",", "Malformed macro"
            statements.append((primitive, row[2:]))
        self.macros[name] = Macro(statements)
