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

import warnings
from pathlib import Path

import pytest

import aab
import aab.config
from aab.config import Config
from aab.project import (
    Project,
    ProjectLayoutError,
    ProjectNotFoundError,
    find_manifest,
)

from .conftest import MODULE_NAME, PACKAGE_SUBDIR


def test_find_manifest_climbs_to_nearest(package_project: Path):
    nested = package_project / PACKAGE_SUBDIR / "designer"
    assert find_manifest(nested) == package_project / "addon.json"
    assert find_manifest(package_project) == package_project / "addon.json"


def test_find_manifest_nearest_wins(package_project: Path):
    inner = package_project / PACKAGE_SUBDIR / "addon.json"
    inner.write_text((package_project / "addon.json").read_text())
    assert find_manifest(package_project / PACKAGE_SUBDIR / "designer") == inner
    assert find_manifest(package_project) == package_project / "addon.json"


def test_find_manifest_none(tmp_path: Path):
    assert find_manifest(tmp_path) is None


def test_discover_raises_outside_project(tmp_path: Path):
    with pytest.raises(ProjectNotFoundError) as excinfo:
        Project.discover(tmp_path)
    assert str(tmp_path) in str(excinfo.value)
    assert "--project" in str(excinfo.value)


def test_flat_layout_defaults(flat_project: Path):
    project = Project.discover(flat_project / "designer")

    assert project.root == flat_project
    assert project.manifest_path == flat_project / "addon.json"
    assert project.package_dir == flat_project
    assert project.package_src == flat_project / "src" / MODULE_NAME
    assert project.out_dir == flat_project / "build"
    assert project.dist_dir == flat_project / "build" / "dist"
    assert project.dist_src == flat_project / "build" / "dist" / "src" / MODULE_NAME
    assert project.module_name == MODULE_NAME


def test_package_layout(package_project: Path):
    project = Project.discover(package_project / PACKAGE_SUBDIR)

    assert project.root == package_project
    assert project.package_dir == package_project / PACKAGE_SUBDIR
    assert project.package_src == package_project / PACKAGE_SUBDIR / "src" / MODULE_NAME
    # Build output stays at the root
    assert project.dist_dir == package_project / "build" / "dist"
    assert project.out_dir == package_project / "build"


@pytest.mark.parametrize(
    "value",
    ["", "/abs/path", "..", "../sibling", "a/../..", "build/dist", "build/dist/x"],
)
def test_invalid_package_dir(flat_project: Path, value: str):
    config = Config(flat_project / "addon.json")
    config["package_dir"] = value
    with pytest.raises(ProjectLayoutError):
        Project.load(flat_project / "addon.json")


def test_package_dir_symlink_outside_root_rejected(flat_project: Path, tmp_path: Path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (flat_project / "linked").symlink_to(outside, target_is_directory=True)
    config = Config(flat_project / "addon.json")
    config["package_dir"] = "linked"
    with pytest.raises(ProjectLayoutError):
        Project.load(flat_project / "addon.json")


def test_package_dir_symlink_into_dist_rejected(flat_project: Path):
    dist = flat_project / "build" / "dist"
    dist.mkdir(parents=True)
    (flat_project / "python").symlink_to(dist, target_is_directory=True)
    config = Config(flat_project / "addon.json")
    config["package_dir"] = "python"
    with pytest.raises(ProjectLayoutError):
        Project.load(flat_project / "addon.json")


def test_package_dir_normalized(flat_project: Path):
    config = Config(flat_project / "addon.json")
    config["package_dir"] = "./python/../python/"
    project = Project.load(flat_project / "addon.json")
    assert project.package_dir == flat_project / "python"


def test_config_without_path_discovers_from_cwd(flat_project: Path, monkeypatch):
    monkeypatch.chdir(flat_project / "designer")
    config = Config()
    assert config.path == flat_project / "addon.json"
    assert config["module_name"] == MODULE_NAME


def test_config_without_path_outside_project(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ProjectNotFoundError):
        Config()


def test_deprecated_module_paths_keep_cwd_semantics(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert aab.PATH_PROJECT_ROOT == tmp_path
        assert aab.PATH_DIST == tmp_path / "build" / "dist"
        assert aab.config.PATH_CONFIG == tmp_path / "addon.json"
    assert len(caught) == 3
    assert all(w.category is DeprecationWarning for w in caught)
    with pytest.raises(AttributeError):
        aab.NO_SUCH_NAME
