"""Setuptools commands for generated package resources."""

from pathlib import Path

from setuptools.command.build_py import build_py


class BuildPy(build_py):
    """Copy canonical repository metadata into the built package."""

    def run(self):
        super().run()
        source = Path(__file__).parent / 'codemeta.json'
        destination = Path(self.build_lib) / 'h5rdmtoolbox' / 'data' / 'codemeta.json'
        self.mkpath(str(destination.parent))
        self.copy_file(str(source), str(destination))
