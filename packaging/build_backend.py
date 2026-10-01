"""Keep the modern backend while providing a Python 3.6/3.7 build path."""

import sys

if sys.version_info < (3, 8):
    from setuptools import build_meta as _backend
else:
    from scikit_build_core import build as _backend

build_wheel = _backend.build_wheel
build_sdist = _backend.build_sdist
prepare_metadata_for_build_wheel = _backend.prepare_metadata_for_build_wheel
get_requires_for_build_wheel = _backend.get_requires_for_build_wheel
get_requires_for_build_sdist = _backend.get_requires_for_build_sdist

if hasattr(_backend, "build_editable"):
    build_editable = _backend.build_editable
    get_requires_for_build_editable = _backend.get_requires_for_build_editable
    prepare_metadata_for_build_editable = _backend.prepare_metadata_for_build_editable
