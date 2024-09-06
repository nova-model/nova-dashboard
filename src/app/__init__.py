import importlib.metadata

from .main import main
from .main_class import MainClass

__all__ = ["MainClass", "main"]

__version__ = importlib.metadata.version(__package__)
