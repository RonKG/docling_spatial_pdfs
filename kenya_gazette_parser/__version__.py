"""Single source of truth for kenya_gazette_parser version constants.

Both ``kenya_gazette_parser.__version__`` and ``pyproject.toml`` read the
library version from this file. The ``LIBRARY_VERSION`` alias exists so
legacy notebook callers that used to declare ``LIBRARY_VERSION = "0.1.0"``
can switch to ``from kenya_gazette_parser import __version__ as LIBRARY_VERSION``
or ``from kenya_gazette_parser.identity import LIBRARY_VERSION``.

``SCHEMA_VERSION`` pins the envelope JSON shape version independently of the
library version (library can bump without breaking the envelope contract).
Contract section 7 fixes it at "1.0" for the 1.0 milestone.
"""

__version__ = "0.1.0"
LIBRARY_VERSION = __version__
SCHEMA_VERSION = "1.0"
