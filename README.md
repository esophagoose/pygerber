# Python Gerber Library
This library provides a simple and elegant parser for Gerber and NC Drill files. It's written in pure Python and supports all Gerber commands, including most deprecated ones.

# File Structure
```
.
├── pygerber
│   ├── aperture.py
│   ├── drill_layer.py
│   ├── gerber_layer.py
│   └── renderers
│   │   |   # Renders a Gerber file as an SVG
│   │   └── svg.py
│   └── standards
│       │   # Enums of Gerber file format
│       ├── gerber.py
│       |   # Enums of NC Drill file format
│       └── nc_drill.py
└── tests
    |   # All unit tests for this package
    └── test_package.py  
```

# Features
- [x] Gerber X2 file parser
    - [x] Reading gerber layer
    - [x] Writing gerber layer
- [x] NC Drill file parser
    - [x] Reading X2 standard files
    - [x] Writing drill files
    - [x] API for drill operations
    - [x] API for rout operations
- [ ] SVG rendering
    - [x] Drill operations
    - [x] Linear rout operations
    - [ ] Circular rout operations
    - [x] Gerber flash operations
    - [x] Gerber linear interpolations
    - [ ] Gerber circular interpolations

# Running Unit Tests
Place gerber files in the `testdata` folder and run the unit tests:
```
pytest
```

# References
- [Gerber Standard](https://www.ucamco.com/files/downloads/file_en/399/the-gerber-file-format-specification-revision-2020-09_en.pdf)
- [NC Drill Standard](https://www.ucamco.com/files/downloads/file_en/305/xnc-format-specification_en.pdf)

