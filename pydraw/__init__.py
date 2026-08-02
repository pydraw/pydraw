from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pydraw")  # single source of truth: the installed package metadata
except PackageNotFoundError:
    __version__ = "0.0.0"

from pydraw.overload import overload
from pydraw.errors import *
from pydraw.util import *
from pydraw.color import Color
from pydraw.location import Location
from pydraw.screen import Screen
from pydraw.scene import Scene
from pydraw.objects import *
# Networking is opt-in: `from pydraw.network import *`. Keeping it out of here means
# an ordinary drawing program never imports socket/threading/select, and the names a
# beginner meets stay to the ones they use.
# from pydraw.sound import Sound