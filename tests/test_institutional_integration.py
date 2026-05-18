try:
    import torch
except ImportError:
    torch = None
import pytest

pytestmark = pytest.mark.skipif(torch is None, reason="torch not installed")
