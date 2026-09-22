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
Shared fixtures: sample projects in both layouts, git helpers, in-process CLI.
"""

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from shutil import copytree
from typing import List, Optional

import pytest

from aab.cli import main
from aab.project import ENV_PROJECT

from . import SAMPLE_PROJECT_NAME, SAMPLE_PROJECT_ROOT

MODULE_NAME = "sample_project"
PACKAGE_SUBDIR = "python"

requires_git = pytest.mark.skipif(shutil.which("git") is None, reason="git missing")
requires_pyuic6 = pytest.mark.skipif(
    shutil.which("pyuic6") is None, reason="pyuic6 (PyQt6) missing"
)


def _add_module(package_dir: Path):
    module_dir = package_dir / "src" / MODULE_NAME
    module_dir.mkdir(parents=True)
    (module_dir / "__init__.py").write_text("", encoding="utf-8")


@pytest.fixture
def flat_project(tmp_path: Path) -> Path:
    """Classic layout: addon.json, src/, designer/, resources/ in one directory"""
    root = tmp_path / SAMPLE_PROJECT_NAME
    copytree(SAMPLE_PROJECT_ROOT, root)
    _add_module(root)
    return root


@pytest.fixture
def package_project(tmp_path: Path) -> Path:
    """Package layout: addon.json at the root, sources under python/"""
    root = tmp_path / "package-project"
    package_dir = root / PACKAGE_SUBDIR
    copytree(SAMPLE_PROJECT_ROOT, package_dir)
    _add_module(package_dir)
    manifest = json.loads((package_dir / "addon.json").read_text(encoding="utf-8"))
    (package_dir / "addon.json").unlink()
    manifest["package_dir"] = PACKAGE_SUBDIR
    (root / "addon.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return root


def git(args: List[str], cwd: Path) -> bytes:
    env = dict(os.environ)
    env.update(
        GIT_AUTHOR_NAME="aab tests",
        GIT_AUTHOR_EMAIL="aab@example.com",
        GIT_COMMITTER_NAME="aab tests",
        GIT_COMMITTER_EMAIL="aab@example.com",
    )
    return subprocess.check_output(
        ["git", "-c", "commit.gpgsign=false"] + args, cwd=str(cwd), env=env
    )


def git_init(root: Path, tag: str = "v0.1.0"):
    """Turn `root` into a git repository with one tagged commit"""
    git(["init", "-q"], root)
    git(["add", "-A"], root)
    git(["commit", "-q", "-m", "Initial commit"], root)
    git(["tag", tag], root)


class CliRunner:
    """Run the aab CLI in-process from a given working directory"""

    def __init__(self, monkeypatch, capsys):
        self._monkeypatch = monkeypatch
        self._capsys = capsys

    def __call__(
        self, args: List[str], cwd: Path, env: Optional[dict] = None
    ) -> "CliResult":
        self._monkeypatch.chdir(cwd)
        self._monkeypatch.delenv(ENV_PROJECT, raising=False)
        for name, value in (env or {}).items():
            self._monkeypatch.setenv(name, value)
        self._capsys.readouterr()
        # main() configures the root logger once per process; reset it so each
        # invocation logs to the stream capsys currently provides
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        try:
            main(args)
            code = 0
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
        return CliResult(code, self._capsys.readouterr().out)


class CliResult:
    def __init__(self, code: int, out: str):
        self.code = code
        self.out = out


@pytest.fixture
def run_cli(monkeypatch, capsys) -> CliRunner:
    return CliRunner(monkeypatch, capsys)
