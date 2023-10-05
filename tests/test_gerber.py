import os
import pytest
import logging

# import gerber_layer as gl
import standard.nc_drill as drl
# import renderer

logging.basicConfig(level=logging.DEBUG)


DRILL_FILES = [f for f in os.listdir("./testdata") if f[-3:].upper() in drl.FILE_EXT]



class TestGerberLayer:
    # @pytest.mark.parametrize("filename", TEST_FILES)
    # def test_read_gerber_layer(self, filename):
    #     layer = gl.GerberLayer(f"./testdata/{filename}")
    #     layer.read(raise_on_unknown_command=True)

    # @pytest.mark.parametrize("filename", TEST_FILES)
    # def test_renderer(self, filename):
    #     layer = gl.GerberLayer(f"./testdata/{filename}")
    #     layer.read()
    #     renderer.RenderSvg(layer)

    @pytest.mark.parametrize("filename", DRILL_FILES)
    def test_renderer(self, filename):
        layer = drl.NCDrill(f"./testdata/{filename}")
        layer.read()


if __name__ == "__main__":
    pytest.main(["-v", "test_gerber_layer.py"])
