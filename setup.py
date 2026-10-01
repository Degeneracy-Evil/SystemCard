"""Legacy Python build adapter; project metadata lives in pyproject.toml."""

import subprocess
import sys
from pathlib import Path

import pybind11
import tomli
from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext

ROOT = Path(__file__).resolve().parent
with (ROOT / "pyproject.toml").open("rb") as metadata_file:
    PROJECT = tomli.load(metadata_file)["project"]


class CMakeBuild(build_ext):
    """Build and install the same native CMake target as the modern backend."""

    def build_extension(self, ext: Extension) -> None:
        output = Path(self.get_ext_fullpath(ext.name)).resolve().parent.parent
        build = Path(self.build_temp).resolve()
        build.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "cmake",
                "-S",
                str(ROOT),
                "-B",
                str(build),
                "-DCMAKE_BUILD_TYPE=Release",
                "-DCMAKE_INSTALL_PREFIX=" + str(output),
                "-DPython_EXECUTABLE=" + sys.executable,
                "-Dpybind11_DIR=" + pybind11.get_cmake_dir(),
            ],
            check=True,
        )
        subprocess.run(["cmake", "--build", str(build), "--parallel", "2"], check=True)
        subprocess.run(["cmake", "--install", str(build)], check=True)


setup(
    name=PROJECT["name"],
    version=PROJECT["version"],
    description=PROJECT["description"],
    long_description=(ROOT / PROJECT["readme"]).read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    license=PROJECT["license"]["text"],
    python_requires=PROJECT["requires-python"],
    install_requires=PROJECT["dependencies"],
    packages=find_packages("src"),
    package_dir={"": "src"},
    package_data={"systemcard": ["*.pyi", "py.typed"]},
    ext_modules=[Extension("systemcard._native", sources=[])],
    cmdclass={"build_ext": CMakeBuild},
    entry_points={"console_scripts": ["systemcard=" + PROJECT["scripts"]["systemcard"]]},
)
