import logging
import os
import tempfile

import pytest

import pygerber.drill_layer as drl
import pygerber.gerber_layer as gl
import pygerber.renderers.svg as renderer
import pygerber.standards.nc_drill as ds

logging.basicConfig(level=logging.DEBUG)

TEST_FILES = os.listdir("./testdata")
DRILL_FILES = [f for f in TEST_FILES if f[-3:].upper() in ds.FILE_EXTENSIONS]
GERBER_FILES = [f for f in TEST_FILES if f[-3:].upper() not in ds.FILE_EXTENSIONS]


class TestPythonGerber:
    @pytest.mark.parametrize("filename", GERBER_FILES)
    def test_read_gerber_layer(self, filename):
        layer = gl.GerberLayer()
        layer.read(f"./testdata/{filename}", raise_on_unknown_command=True)

    @pytest.mark.parametrize("filename", GERBER_FILES)
    def test_renderer(self, filename):
        layer = gl.GerberLayer()
        layer.read(f"./testdata/{filename}")
        renderer.SvgLayerRenderer(layer)

    @pytest.mark.parametrize("filename", DRILL_FILES)
    def test_drill_layer_read(self, filename):
        layer = drl.DrillLayer()
        layer.read(f"./testdata/{filename}")

    def test_drill_layer_write(self):
        layer = drl.DrillLayer()
        layer.read("./testdata/Test_Drill.drl")

        with tempfile.NamedTemporaryFile() as output_file:
            layer.write(output_file.name)
            new_layer = drl.DrillLayer()
            new_layer.read(output_file.name)
            assert layer.operations == new_layer.operations


if __name__ == "__main__":
    pytest.main(["-v", "test_gerber_layer.py"])
