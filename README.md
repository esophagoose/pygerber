# Python Gerber Library
This library provides a simple and elegant parser for Gerber and NC Drill files. It's written in pure Python and supports all Gerber commands, including most deprecated ones.

# Features
- [x] Gerber X2 file parser
    - [x] Reading gerber layer
    - [ ] Writing gerber layer
    - [ ] SVG rendering (in-progress)
- [ ] NC Drill file parser
    - [x] Reading X2 standard files
    - [x] Writing drill files
    - [ ] SVG rendering of drill files


# Running Unit Tests
Place gerber files in the `testdata` folder and run the unit tests:
```
pytest
```

# References
- [Gerber Standard](https://www.ucamco.com/files/downloads/file_en/399/the-gerber-file-format-specification-revision-2020-09_en.pdf)
- [NC Drill Standard](https://www.ucamco.com/files/downloads/file_en/305/xnc-format-specification_en.pdf)

