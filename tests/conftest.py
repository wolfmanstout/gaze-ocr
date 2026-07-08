"""Pytest path setup so these tests run without installing the package.

In the talon-gaze-ocr repository, gaze-ocr and its dependencies are vendored
as sibling subtrees rather than installed into the environment. Append them to
sys.path so the root repository's test command can run these tests directly.
In the standalone gaze-ocr repository the sibling paths don't exist and the
installed packages are used instead.
"""

import sys
from pathlib import Path

_package_root = Path(__file__).resolve().parents[1]
_subtrees = _package_root.parent
for _path in [
    _package_root,
    _subtrees / "screen-ocr",
    _subtrees / "rapidfuzz" / "src",
]:
    if _path.is_dir() and str(_path) not in sys.path:
        # Append so installed (potentially faster binary) packages take
        # precedence when available.
        sys.path.append(str(_path))
