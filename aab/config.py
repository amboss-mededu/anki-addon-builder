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
Project config parser
"""

import json
import logging
import warnings
from collections import UserDict
from pathlib import Path
from typing import Any, Optional

import jsonschema
from jsonschema.exceptions import ValidationError

from . import PATH_PACKAGE

MANIFEST_NAME = "addon.json"


def __getattr__(name: str) -> Any:
    if name == "PATH_CONFIG":
        warnings.warn(
            "aab.config.PATH_CONFIG is deprecated. Use "
            "aab.project.Project.discover().manifest_path instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Path.cwd() / MANIFEST_NAME
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))


class Config(UserDict):

    """
    Simple dictionary-like interface to the add-on manifest (addon.json)
    """

    with (PATH_PACKAGE / "schema.json").open("r", encoding="utf-8") as f:
        _schema = json.loads(f.read())

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            # Legacy constructor: locate the manifest from the working directory
            from .project import ProjectNotFoundError, find_manifest

            path = find_manifest(Path.cwd())
            if path is None:
                raise ProjectNotFoundError(Path.cwd())
        self._path = Path(path)
        try:
            with self._path.open(encoding="utf-8") as f:
                data = json.loads(f.read())
            jsonschema.validate(data, self._schema)
            self.data = data
        except (IOError, OSError, ValueError, ValidationError):
            logging.error(
                "Error: Could not read '{}'. Traceback follows below:\n".format(
                    self._path
                )
            )
            raise

    @property
    def path(self) -> Path:
        return self._path

    def __setitem__(self, name, value):
        self.data[name] = value
        self._write(self.data)

    def _write(self, data):
        try:
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=False)
        except (IOError, OSError):
            logging.error(
                "Error: Could not write to '{}'. Traceback follows below:\n".format(
                    self._path
                )
            )
            raise
