import os
import pytest

import gerber_layer as gl

TEST_FILES = [f for f in os.listdir("./testdata") if f != "README.md"]


class TestGerberLayer:
    @pytest.mark.parametrize("filename", TEST_FILES)
    def test_read_gerber_layer(self, filename):
        layer = gl.GerberLayer(f"./testdata/{filename}")
        if layer.file_type == "drill":
            return
        layer.read()


if __name__ == "__main__":
    pytest.main(["-v", "test_gerber_layer.py"])