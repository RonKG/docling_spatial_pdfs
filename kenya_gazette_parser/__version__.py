"""Single source of truth for the kenya_gazette_parser version string.

Both ``kenya_gazette_parser.__version__`` and ``pyproject.toml`` read from here.
The notebook's ``LIBRARY_VERSION`` constant (F14) will switch to importing this
value at F20; until then the two ``"0.1.0"`` strings must be kept in sync by hand.
"""

__version__ = "0.1.0"
