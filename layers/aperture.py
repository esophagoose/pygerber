import enum
import logging
import math
import re
from typing import Any, Dict, List, NamedTuple, Tuple


class ApertureCircle(NamedTuple):
    diameter: float
    cx: float = 0
    cy: float = 0

    @property
    def r(self):
        return self.diameter / 2


class ApertureRectangle(NamedTuple):
    width: float
    height: float
    cx: float = 0
    cy: float = 0
    rotation: float = 0


class ApertureObround(NamedTuple):
    width: float
    height: float
    cx: float = 0
    cy: float = 0


class AperturePolygon(NamedTuple):
    diameter: float
    vertices: int
    rotation: float = 0
    cx: float = 0
    cy: float = 0


class ApertureOutline(NamedTuple):
    points: Tuple[int]
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


class Aperture(NamedTuple):
    index: str
    exposure: bool
    shape: Any
    rotation: float = 0
    hole: float = 0
    comments: List[str] = []


class Macro(NamedTuple):
    name: str
    statements: List[Tuple[MacroPrimitive, str]]

    def validate_values(self, values):
        data = [text for _, text in self.statements]
        results = re.findall(r"\$(\d+)", " ".join(data))
        count = len(set(results))
        error = f"Invalid values! Got {len(values)}, expected {count}"
        assert count == len(values), error

    def _parse(self, values: List[float]):
        parsed = []
        for p, statement in self.statements:
            for i, value in enumerate(values):
                statement = statement.replace(f"${i + 1}", str(value))
            parsed.append((p, [float(v) for v in statement.split(",")]))
        return parsed

    def generate_aperture(self, index: int, values: List[float], comments):
        self.validate_values(values)
        shapes = []
        for primitive, statement in self._parse(values):
            shape = None
            exposure = True
            rotation = 0
            if primitive == MacroPrimitive.CIRCLE:
                exposure, diameter, cx, cy, rotation = statement
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
                points = [
                    (statement[i], statement[i + 1])
                    for i in range(2, len(statement) - 1, 2)
                ]
                assert len(points) == verticies, "Malformed command"
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
            shapes.append(shape)
        return Aperture(index, exposure, shapes, rotation, 0, comments)

    def from_aperture(self, aperture: Aperture):
        for i, shape in enumerate(aperture.shape):
            primitive, statement = self.statements[i]
            variables = set(re.findall(r"\$\d+", statement))
            variable_indicies = []
            for variable in sorted(variables):
                variable_indicies.append(statement.split(",").index(variable))
            if primitive == MacroPrimitive.CIRCLE:
                values = [
                    aperture.exposure,
                    shape.diameter,
                    shape.cx,
                    shape.cy,
                    aperture.rotation,
                ]
            elif primitive == MacroPrimitive.VECTOR_LINE:
                raise NotImplementedError(MacroPrimitive.VECTOR_LINE)
            elif primitive == MacroPrimitive.CENTER_LINE:
                raise NotImplementedError(MacroPrimitive.CENTER_LINE)
            elif primitive == MacroPrimitive.OUTLINE:
                values = [aperture.exposure, len(shape.points) - 1]
                values.extend([x for p in shape.points for x in p])
                values.append(aperture.rotation)
            elif primitive == MacroPrimitive.POLYGON:
                values = [
                    aperture.exposure,
                    shape.vertices,
                    shape.cx,
                    shape.cy,
                    shape.diameter,
                    aperture.rotation,
                ]
            elif primitive == MacroPrimitive.MOIRE:
                raise NotImplementedError(MacroPrimitive.MOIRE)
            elif primitive == MacroPrimitive.THERMAL:
                raise NotImplementedError(MacroPrimitive.THERMAL)
            else:
                raise NotImplementedError(statement)
            parsed = "X".join([str(values[i]) for i in variable_indicies])
            return f"{self.name},{parsed}"


class ApertureFactory:
    def __init__(self):
        self.macros: Dict[str, Macro] = {}
        self._macro_map: Dict[str, int] = {}

    def from_aperture_define(self, statement, comments=[]):
        def pad_optional_params(params: List[float], count: int):
            return params + [0] * (count - len(params))

        pattern = re.compile(r"^D(\d+)([A-z]+),([\d.X]+)$")
        aperture_id, shape, params = pattern.findall(statement)[0]
        parameters = [float(p) for p in params.split("X")]
        hole = 0
        if shape in self.macros:
            macro = self.macros[shape]
            self._macro_map[int(aperture_id)] = shape
            return macro.generate_aperture(int(aperture_id), parameters, comments)
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
            index=int(aperture_id),
            exposure=True,
            shape=shape,
            rotation=0,
            hole=hole,
            comments=comments,
        )

    def to_aperture_define(self, aperture: Aperture) -> str:
        if isinstance(aperture.shape, list):
            # Handling macros
            shape = self._macro_map[int(aperture.index)]
            macro = self.macros[shape]
            define = macro.from_aperture(aperture)
            return f"ADD{aperture.index}{define}"
        else:
            shape = type(aperture.shape).__name__.replace("Aperture", "")[0]
            params = "X".join(
                str(p)
                for p in aperture.shape._asdict().values()
                if isinstance(p, float) and p != 0
            )
            return f"ADD{aperture.index}{shape},{params}"

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
        self.macros[name] = Macro(name, statements)

    def macro_to_str(self, macro: Macro) -> str:
        statement = f"%AM{macro.name}*\n"
        for primitive, params in macro.statements:
            statement += f"{primitive.value},{params}*\n"
        statement += "%"
        return statement
