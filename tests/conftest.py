import os
import sys

# Ensure that tests/stubs is prepended to sys.path so our minimal "homeassistant" stub is importable
STUBS = os.path.join(os.path.dirname(__file__), "stubs")
if STUBS not in sys.path:
    sys.path.insert(0, STUBS)
