"""Pytest configuration — make the project root importable for the test suite.

Ensures `import agent.tools` works whether or not the package is installed,
without requiring a separate editable install step.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
