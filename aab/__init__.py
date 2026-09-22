# -*- coding: utf-8 -*-

# Anki Add-on Builder
#
# Copyright (C)  2016-2021 Aristotelis P. <https://glutanimate.com/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version, with the additions
# listed at the end of the license file that accompanied this program.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# NOTE: This program is subject to certain additional terms pursuant to
# Section 7 of the GNU Affero General Public License.  You should have
# received a copy of these additional terms immediately following the
# terms and conditions of the GNU Affero General Public License that
# accompanied this program.
#
# If not, please request a copy through one of the means of contact
# listed here: <https://glutanimate.com/contact/>.
#
# Any modifications to this file must keep this entire header intact.

"""
Handles build tasks for Anki add-ons, including packaging them
to be distributed through AnkiWeb or other channels.

This script presupposes that you have a proper development environment
set up for the Anki version you are targeting, including having tools
like pyrcc4 and pyuic4 (Anki 2.0) or pyrcc5 and pyuic5 (Anki 2.1) in
your PATH.

For instructions on how to set up a development environment for Anki
please refer to Anki's documentation.
"""

import warnings
from pathlib import Path
from typing import Any

# Meta

__version__ = "1.0.0-dev.5"
__author__ = "Aristotelis P. (Glutanimate)"
__title__ = "Anki Add-on Builder"
__homepage__ = "https://glutanimate.com"

COPYRIGHT_MSG = """\
{title} v{version}

Copyright (C) 2016-2022  {author}  <{homepage}>

This program comes with ABSOLUTELY NO WARRANTY;
This is free software, and you are welcome to redistribute it
under certain conditions; For details please see the LICENSE file.
""".format(
    title=__title__, version=__version__, author=__author__, homepage=__homepage__
)

# Global variables

PATH_PACKAGE = Path(__file__).resolve().parent
DIST_TYPES = ["local", "ankiweb"]


# Deprecated module-level project paths
#
# The project root used to be computed from the current working directory at
# import time. Projects are now resolved explicitly, see aab.project.Project.
# The old names are kept with their cwd-based semantics and a deprecation warning.

_DEPRECATED_PATHS = {
    "PATH_PROJECT_ROOT": lambda: Path.cwd(),
    "PATH_DIST": lambda: Path.cwd() / "build" / "dist",
}


def __getattr__(name: str) -> Any:
    if name in _DEPRECATED_PATHS:
        warnings.warn(
            "aab.{} is deprecated. Use aab.project.Project.discover() instead.".format(
                name
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return _DEPRECATED_PATHS[name]()
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))
