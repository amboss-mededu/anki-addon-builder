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

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import COPYRIGHT_MSG, DIST_TYPES
from .builder import AddonBuilder, clean_project
from .git import Git
from .manifest import ManifestUtils
from .project import ENV_PROJECT, Project, ProjectError, find_manifest
from .ui import QtVersion, UIBuilder

_HINT_PACKAGE = "Check the package_dir setting in addon.json."
_HINT_DIST = "Run `aab create_dist` first."


# Helpers
##############################################################################


def _env_default(name: str) -> Optional[str]:
    return os.environ.get(name) or None


def _fail(message: str):
    print("Error: {}".format(message))
    sys.exit(1)


def _require_dir(path: Path, description: str, hint: str):
    if not path.is_dir():
        _fail("{} not found at {}. {}".format(description, path, hint))


def get_qt_versions(args: argparse.Namespace, project: Project) -> List[QtVersion]:
    targets = [args.target] if args.target != "all" else project.config["targets"]

    if "anki21" in targets:
        qt_versions = [QtVersion.qt5, QtVersion.qt6]
    else:
        qt_versions = [QtVersion[key] for key in targets]

    return qt_versions


def get_dist_types(args: argparse.Namespace) -> List[str]:
    return [args.dist] if args.dist != "all" else DIST_TYPES


# Entry points
##############################################################################


def build(project: Project, args: argparse.Namespace):
    _require_dir(project.package_dir, "Package directory", _HINT_PACKAGE)
    qt_versions = get_qt_versions(args, project)
    dists = get_dist_types(args)

    builder = AddonBuilder(version=args.version, project=project)

    for cnt, dist in enumerate(dists, start=1):
        logging.info("\n=== Build task %s/%s ===", cnt, len(dists))
        builder.build(qt_versions=qt_versions, disttype=dist)


def ui(project: Project, args: argparse.Namespace):
    _require_dir(project.package_dir, "Package directory", _HINT_PACKAGE)
    qt_versions = get_qt_versions(args, project)

    builder = UIBuilder(dist=project.package_dir, config=project.config)

    for cnt, qt_version in enumerate(qt_versions, start=1):
        logging.info("\n=== Build task %s/%s ===\n", cnt, len(qt_versions))
        builder.build(qt_version=qt_version)

    logging.info("\n=== Writing Qt compatibility shim ===")
    builder.create_qt_shim()
    logging.info("Done.")


def manifest(project: Project, args: argparse.Namespace):
    if args.dist == "all":
        print("'all' is not supported as a dist_type value when building the manifest.")
        return False

    _require_dir(project.package_src, "Add-on module directory", _HINT_PACKAGE)

    git = Git(project.root)
    version = git.parse_version(vstring=args.version)

    ManifestUtils.generate_and_write_manifest(
        addon_properties=project.config,
        version=version,
        dist_type=args.dist,
        target_dir=project.package_src,
        git=git,
    )


def create_dist(project: Project, args: argparse.Namespace):
    _require_dir(project.package_dir, "Package directory", _HINT_PACKAGE)
    builder = AddonBuilder(version=args.version, project=project)
    builder.create_dist()


def build_dist(project: Project, args: argparse.Namespace):
    _require_dir(project.dist_dir, "Dist directory", _HINT_DIST)
    qt_versions = get_qt_versions(args, project)
    dists = get_dist_types(args)

    builder = AddonBuilder(version=args.version, project=project)

    for cnt, dist in enumerate(dists, start=1):
        logging.info("\n=== Build task %s/%s ===", cnt, len(dists))
        builder.build_dist(qt_versions=qt_versions, disttype=dist)


def package_dist(project: Project, args: argparse.Namespace):
    _require_dir(project.dist_dir, "Dist directory", _HINT_DIST)
    qt_versions = get_qt_versions(args, project)
    dists = get_dist_types(args)

    builder = AddonBuilder(version=args.version, project=project)

    for cnt, dist in enumerate(dists, start=1):
        logging.info("\n=== Build task %s/%s ===", cnt, len(dists))
        builder.package_dist(qt_versions=qt_versions, disttype=dist)


def clean(project: Project, args: argparse.Namespace):
    clean_project(project)


# Argument parsing
##############################################################################


def construct_parser():
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=None)
    subparsers = parser.add_subparsers()

    parser.add_argument(
        "-v",
        "--verbose",
        help="Enable verbose output",
        required=False,
        action="store_true",
    )
    parser.add_argument(
        "--project",
        metavar="DIR",
        help=(
            "Directory to start looking for the add-on project in. aab walks up "
            "from there until it finds an addon.json. Defaults to the current "
            "working directory. [env: {env}]".format(env=ENV_PROJECT)
        ),
        default=_env_default(ENV_PROJECT),
    )

    target_parent = argparse.ArgumentParser(add_help=False)
    target_parent.add_argument(
        "-t",
        "--target",
        help=(
            "Anki release type to build for. Use 'all' (deprecated alias: 'anki21') to"
            " target both Qt5 and Qt6."
        ),
        type=str,
        default="all",
        choices=["qt6", "qt5", "all", "anki21"],
    )

    dist_parent = argparse.ArgumentParser(add_help=False)
    dist_parent.add_argument(
        "-d",
        "--dist",
        help="Distribution channel to build for",
        type=str,
        default="local",
        choices=["local", "ankiweb", "all"],
    )

    build_parent = argparse.ArgumentParser(add_help=False)
    build_parent.add_argument(
        "version",
        nargs="?",
        help=(
            "Version to (pre-)build as a git reference "
            "(e.g. 'v1.2.0' or 'd338f6405'). "
            "Special keywords: 'dev' - working directory, "
            "'current' – latest commit, 'release' – latest tag. "
            "Leave empty to build latest tag."
        ),
    )

    build_group = subparsers.add_parser(
        "build",
        parents=[build_parent, target_parent, dist_parent],
        help="Build and package add-on for distribution",
    )
    build_group.set_defaults(func=build)

    ui_group = subparsers.add_parser(
        "ui", parents=[target_parent], help="Compile add-on user interface files"
    )
    ui_group.set_defaults(func=ui)

    manifest_group = subparsers.add_parser(
        "manifest",
        parents=[build_parent, dist_parent],
        help="Generate manifest file from add-on properties in addon.json",
    )
    manifest_group.set_defaults(func=manifest)

    clean_group = subparsers.add_parser("clean", help="Clean leftover build files")
    clean_group.set_defaults(func=clean)

    create_dist_group = subparsers.add_parser(
        "create_dist",
        parents=[build_parent, target_parent, dist_parent],
        help=(
            "Prepare source tree distribution for building under build/dist. "
            "This is intended to be used in build scripts and should be run before "
            "`build_dist` and `package_dist`."
        ),
    )
    create_dist_group.set_defaults(func=create_dist)

    build_dist_group = subparsers.add_parser(
        "build_dist",
        parents=[build_parent, target_parent, dist_parent],
        help=(
            "Build add-on files from prepared source tree under build/dist. "
            "This step performs all source code post-processing handled by "
            "aab itself (e.g. building the Qt UI and writing the add-on manifest). "
            "As with `create_dist` and `package_dist`, this command is meant to be "
            "used in build scripts where it can provide an avenue for performing "
            "additional processing ahead of packaging the add-on."
        ),
    )
    build_dist_group.set_defaults(func=build_dist)

    package_dist_group = subparsers.add_parser(
        "package_dist",
        parents=[build_parent, target_parent, dist_parent],
        help=(
            "Package pre-built distribution of add-on files under build/dist into "
            "a distributable .ankiaddon package. This is inteded to be used in "
            "build scripts and called after both `create_dist` and `build_dist` "
            "have been run."
        ),
    )
    package_dist_group.set_defaults(func=package_dist)

    return parser


# Main
##############################################################################


def _load_project(args: argparse.Namespace) -> Project:
    try:
        start = args.project if args.project else Path.cwd()
        return Project.discover(start)
    except (ProjectError, OSError) as e:
        _fail(str(e))
        raise  # unreachable, keeps type checkers happy


def _warn_if_inside_dist(project: Project):
    """
    An exported dist of a flat-layout project carries its own addon.json, so
    running aab inside it resolves the dist as a project of its own (as it
    always did). Point that out, since it is rarely what the user wants.
    """
    try:
        outer_manifest = find_manifest(project.root.parent)
    except OSError:
        return
    if outer_manifest is None:
        return
    outer_root = outer_manifest.parent
    if _is_within(project.root, outer_root / "build"):
        logging.warning(
            "Running inside the build tree of the project at %s: commands operate "
            "on %s as a project of its own.",
            outer_root,
            project.root,
        )


def _is_within(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def main(argv: Optional[List[str]] = None):
    print(COPYRIGHT_MSG)

    # Argument parsing

    parser = construct_parser()
    args = parser.parse_args(argv)

    # Logging

    if args.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s")

    if args.func is None:
        parser.print_usage()
        return

    # Argument aliases

    if hasattr(args, "target") and args.target == "anki21":
        print(
            "WARNING: 'anki21' is deprecated as a target type. Please use 'all' instead"
            " if targeting both qt6 and qt5 Anki builds."
        )
        args.target = "all"

    # Project

    project = _load_project(args)
    _warn_if_inside_dist(project)

    # Run
    args.func(project, args)


if __name__ == "__main__":
    main()
