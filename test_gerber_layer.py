import os
import pytest
import logging

import gerber_layer as gl


class TestGerberLayer:
    @pytest.mark.parametrize("filename", os.listdir("./testdata"))
    def test_read_gerber_layer(self, filename):
        layer = gl.GerberLayer(f"./testdata/{filename}")
        if layer.file_type == "drill":
            return
        layer.read()

if __name__ == "__main__":
    pytest.main(["-v", "test_gerber_layer.py"])

