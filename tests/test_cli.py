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
End-to-end tests of the CLI. They run in-process: since projects are resolved
per invocation rather than at import time, no subprocess is needed.
"""

import json
import shutil
import zipfile
from pathlib import Path

from . import SAMPLE_PROJECT_ROOT
from .conftest import (
    MODULE_NAME,
    PACKAGE_SUBDIR,
    git_init,
    requires_git,
    requires_pyuic6,
)


def read_manifest(module_dir: Path) -> dict:
    return json.loads((module_dir / "manifest.json").read_text(encoding="utf-8"))


# Discovery
##############################################################################


def test_no_project_found(tmp_path: Path, run_cli):
    result = run_cli(["ui", "-t", "qt6"], cwd=tmp_path)
    assert result.code == 1
    assert "No addon.json found in {}".format(tmp_path) in result.out


def test_no_subcommand_prints_usage(tmp_path: Path, run_cli):
    result = run_cli([], cwd=tmp_path)
    assert result.code == 0
    assert "usage: " in result.out


@requires_pyuic6
def test_commands_climb_to_manifest_from_subdirectory(flat_project: Path, run_cli):
    result = run_cli(["ui", "-t", "qt6"], cwd=flat_project / "designer")
    assert result.code == 0, result.out
    assert (
        flat_project / "src" / MODULE_NAME / "gui" / "forms" / "qt6" / "dialog.py"
    ).is_file()
    assert not (flat_project / "designer" / "src").exists()


@requires_pyuic6
def test_project_flag_and_env(flat_project: Path, tmp_path: Path, run_cli):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    forms = flat_project / "src" / MODULE_NAME / "gui" / "forms"

    result = run_cli(["--project", str(flat_project), "ui", "-t", "qt6"], cwd=elsewhere)
    assert result.code == 0, result.out
    assert (forms / "qt6" / "dialog.py").is_file()

    shutil.rmtree(str(forms))
    result = run_cli(
        ["ui", "-t", "qt6"], cwd=elsewhere, env={"AAB_PROJECT": str(flat_project)}
    )
    assert result.code == 0, result.out
    assert (forms / "qt6" / "dialog.py").is_file()
    assert list(elsewhere.iterdir()) == []


@requires_pyuic6
def test_nearest_manifest_wins(package_project: Path, run_cli):
    package_dir = package_project / PACKAGE_SUBDIR
    inner = json.loads((package_project / "addon.json").read_text(encoding="utf-8"))
    inner.pop("package_dir")
    inner["module_name"] = "inner_project"
    (package_dir / "addon.json").write_text(json.dumps(inner), encoding="utf-8")

    result = run_cli(["ui", "-t", "qt6"], cwd=package_dir / "designer")
    assert result.code == 0, result.out
    assert (
        package_dir / "src" / "inner_project" / "gui" / "forms" / "qt6" / "dialog.py"
    ).is_file()
    assert not (package_dir / "src" / MODULE_NAME / "gui").exists()


# Flat layout: behavior unchanged
##############################################################################


@requires_git
@requires_pyuic6
def test_flat_build_from_root(flat_project: Path, run_cli):
    git_init(flat_project)

    result = run_cli(["build", "-t", "qt6", "-d", "local", "current"], cwd=flat_project)
    assert result.code == 0, result.out

    dist_module = flat_project / "build" / "dist" / "src" / MODULE_NAME
    assert read_manifest(dist_module)["version"] == "v0.1.0"

    package = flat_project / "build" / "sample-project-v0.1.0-qt6.ankiaddon"
    assert package.is_file()
    with zipfile.ZipFile(str(package)) as zf:
        names = set(zf.namelist())
    assert {
        "__init__.py",
        "manifest.json",
        "gui/forms/__init__.py",
        "gui/forms/qt6/__init__.py",
        "gui/forms/qt6/dialog.py",
        "gui/resources/__init__.py",
        "gui/resources/sample-project/icons/help.svg",
        "gui/resources/sample-project/icons/coffee.svg",
    } <= names


def test_source_tree_commands_require_module(flat_project: Path, run_cli):
    shutil.rmtree(str(flat_project / "src"))
    result = run_cli(["manifest", "1.0.0"], cwd=flat_project)
    assert result.code == 1
    assert "Add-on module directory not found" in result.out


def test_dist_commands_require_dist(flat_project: Path, run_cli):
    result = run_cli(["build_dist", "-t", "qt6", "1.0.0"], cwd=flat_project)
    assert result.code == 1
    assert "Dist directory not found" in result.out
    assert "create_dist" in result.out


# Package layout
##############################################################################


@requires_pyuic6
def test_package_layout_ui_builds_into_package(package_project: Path, run_cli):
    package_dir = package_project / PACKAGE_SUBDIR

    result = run_cli(["ui", "-t", "qt6"], cwd=package_dir)
    assert result.code == 0, result.out

    forms = package_dir / "src" / MODULE_NAME / "gui" / "forms"
    assert (forms / "qt6" / "dialog.py").is_file()
    assert (forms / "__init__.py").is_file()
    assert not (package_project / "src").exists()

    # Identical when run from the root
    shutil.rmtree(str(forms))
    result = run_cli(["ui", "-t", "qt6"], cwd=package_project)
    assert result.code == 0, result.out
    assert (forms / "qt6" / "dialog.py").is_file()


@requires_git
@requires_pyuic6
def test_package_layout_dist_pipeline(package_project: Path, run_cli):
    """create_dist exports the package subtree, and the dist commands work on
    it from any directory in the project."""
    git_init(package_project)
    package_dir = package_project / PACKAGE_SUBDIR
    dist = package_project / "build" / "dist"

    (package_project / "LICENSE").write_text("root license", encoding="utf-8")

    result = run_cli(["create_dist", "current"], cwd=package_project)
    assert result.code == 0, result.out
    # Package-shaped: sources at the dist root, no package_dir nesting, no manifest
    assert (dist / "src" / MODULE_NAME / "__init__.py").is_file()
    assert (dist / "designer" / "dialog.ui").is_file()
    assert not (dist / PACKAGE_SUBDIR).exists()
    assert not (dist / "addon.json").exists()

    result = run_cli(
        ["build_dist", "-t", "qt6", "current"], cwd=package_dir / "designer"
    )
    assert result.code == 0, result.out
    dist_module = dist / "src" / MODULE_NAME
    assert read_manifest(dist_module)["version"] == "v0.1.0"
    assert (dist_module / "gui" / "forms" / "qt6" / "dialog.py").is_file()
    # The project-level license reaches the module although the package
    # export does not contain it
    assert (dist_module / "LICENSE.txt").read_text(encoding="utf-8") == "root license"
    # The working tree was left alone
    assert not (package_dir / "src" / MODULE_NAME / "gui").exists()

    result = run_cli(["package_dist", "-t", "qt6", "current"], cwd=package_dir)
    assert result.code == 0, result.out
    package = package_project / "build" / "sample-project-v0.1.0-qt6.ankiaddon"
    assert package.is_file()
    with zipfile.ZipFile(str(package)) as zf:
        assert "gui/forms/qt6/dialog.py" in zf.namelist()


@requires_git
def test_create_dist_when_project_is_below_repository_root(
    package_project: Path, tmp_path: Path, run_cli
):
    """The git repository root and the project root need not coincide"""
    repo = tmp_path / "repo"
    repo.mkdir()
    nested = repo / "addons" / package_project.name
    nested.parent.mkdir()
    shutil.move(str(package_project), str(nested))
    git_init(repo)

    result = run_cli(["create_dist", "current"], cwd=nested / PACKAGE_SUBDIR)
    assert result.code == 0, result.out

    dist = nested / "build" / "dist"
    assert (dist / "src" / MODULE_NAME / "__init__.py").is_file()
    assert (dist / "designer" / "dialog.ui").is_file()
    assert not (dist / "addons").exists()
    assert not (dist / PACKAGE_SUBDIR).exists()


def test_running_inside_exported_flat_dist_warns(flat_project: Path, run_cli):
    dist = flat_project / "build" / "dist"
    shutil.copytree(flat_project, dist)
    result = run_cli(["clean"], cwd=dist)
    assert result.code == 0, result.out
    assert (
        "Running inside the build tree of the project at {}".format(flat_project)
        in result.out
    )


def test_clean_handles_shell_metacharacters_in_path(tmp_path: Path, run_cli):
    root = tmp_path / "$(echo injected)"
    shutil.copytree(SAMPLE_PROJECT_ROOT, root)
    stale = root / "src" / MODULE_NAME / "stale.pyc"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"")

    result = run_cli(["clean"], cwd=root)
    assert result.code == 0, result.out
    assert not stale.exists()
    assert not (tmp_path / "injected").exists()


def test_package_layout_clean_scopes_to_package_and_dist(
    package_project: Path, run_cli
):
    package_dir = package_project / PACKAGE_SUBDIR
    dist = package_project / "build" / "dist"
    dist.mkdir(parents=True)
    stale_in_package = package_dir / "src" / MODULE_NAME / "stale.pyc"
    stale_in_package.write_bytes(b"")
    stale_outside = package_project / "other" / "keep.pyc"
    stale_outside.parent.mkdir()
    stale_outside.write_bytes(b"")

    result = run_cli(["clean"], cwd=package_dir)
    assert result.code == 0, result.out
    assert not dist.exists()
    assert not stale_in_package.exists()
    assert stale_outside.exists()
