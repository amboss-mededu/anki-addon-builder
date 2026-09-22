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
Project discovery and layout

An aab project is a directory tree with an add-on manifest (addon.json) at
its root. The manifest is discovered by walking up from a start directory
(the working directory by default), nearest manifest wins.

The manifest may point at a package directory holding the conventional
source layout (src/<module>, designer/, resources/). It defaults to the
project root itself, which is the classic flat layout. Build output always
lives under the project root.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from .config import MANIFEST_NAME, Config

PathLike = Union[str, "os.PathLike[str]"]

ENV_PROJECT = "AAB_PROJECT"

DEFAULT_PACKAGE_DIR = "."
BUILD_DIR_NAME = "build"
DIST_DIR_NAME = "dist"
SRC_DIR_NAME = "src"


class ProjectError(Exception):
    """Base class for errors while locating or loading a project"""


class ProjectNotFoundError(ProjectError):
    def __init__(self, start: Path):
        self.start = start
        super().__init__(
            "No {manifest} found in {start} or any of its parent directories. "
            "Run aab from inside an add-on project, or pass --project / "
            "{env}.".format(manifest=MANIFEST_NAME, start=start, env=ENV_PROJECT)
        )


class ProjectLayoutError(ProjectError):
    """The manifest describes a layout aab cannot work with"""


def find_manifest(start: PathLike) -> Optional[Path]:
    """
    Return the nearest addon.json at or above `start`, or None if there is none
    up to the filesystem root.
    """
    start_path = Path(os.path.abspath(start))
    for directory in (start_path, *start_path.parents):
        candidate = directory / MANIFEST_NAME
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            # e.g. an ancestor we may traverse but not read; keep climbing
            continue
    return None


@dataclass(frozen=True)
class Project:

    """
    A resolved add-on project.

    root         directory holding addon.json; build output lives below it
    config       the parsed manifest
    package_dir  directory holding src/, designer/ and resources/ (root by default)
    """

    root: Path
    config: Config
    package_dir: Path

    @classmethod
    def discover(cls, start: Optional[PathLike] = None) -> "Project":
        """Locate the manifest by walking up from `start` (default: cwd)"""
        start_path = Path(start) if start is not None else Path.cwd()
        manifest = find_manifest(start_path)
        if manifest is None:
            raise ProjectNotFoundError(Path(os.path.abspath(start_path)))
        return cls.load(manifest)

    @classmethod
    def load(cls, manifest: PathLike) -> "Project":
        """Load the project described by the manifest at `manifest`"""
        manifest_path = Path(os.path.abspath(manifest))
        root = manifest_path.parent
        config = Config(manifest_path)
        package_dir = _resolve_package_dir(
            root, config.get("package_dir", DEFAULT_PACKAGE_DIR)
        )
        project = cls(root=root, config=config, package_dir=package_dir)
        if _is_within(package_dir, project.dist_dir) or _is_within(
            package_dir.resolve(), project.dist_dir.resolve()
        ):
            raise ProjectLayoutError(
                "package_dir must not lie inside the dist directory {}".format(
                    project.dist_dir
                )
            )
        logging.debug("Project root: %s (package: %s)", root, package_dir)
        return project

    @property
    def out_dir(self) -> Path:
        """Where packaged .ankiaddon files are written"""
        return self.root / BUILD_DIR_NAME

    @property
    def dist_dir(self) -> Path:
        """Package-shaped tree that the dist commands operate on"""
        return self.out_dir / DIST_DIR_NAME

    @property
    def manifest_path(self) -> Path:
        return self.config.path

    @property
    def module_name(self) -> str:
        return self.config["module_name"]

    @property
    def package_src(self) -> Path:
        """The add-on module inside the package directory"""
        return self.package_dir / SRC_DIR_NAME / self.module_name

    @property
    def dist_src(self) -> Path:
        """The add-on module inside the dist tree"""
        return self.dist_dir / SRC_DIR_NAME / self.module_name


def _resolve_package_dir(root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise ProjectLayoutError("package_dir must be a non-empty string")
    if os.path.isabs(value):
        raise ProjectLayoutError(
            "package_dir must be relative to the project root, got {!r}".format(value)
        )
    package_dir = Path(os.path.normpath(root / value))
    if not _is_within(package_dir, root) or not _is_within(
        package_dir.resolve(), root.resolve()
    ):
        raise ProjectLayoutError(
            "package_dir must stay inside the project root, got {!r}".format(value)
        )
    return package_dir


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True
