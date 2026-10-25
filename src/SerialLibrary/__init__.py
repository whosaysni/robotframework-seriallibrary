"""Robot Framework library for testing devices over serial ports."""

from .library import SerialLibrary
from .version import __version__

__all__ = ["SerialLibrary", "__version__"]
