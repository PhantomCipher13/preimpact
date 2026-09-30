"""
pytest configuration for PreImpact.
"""
import sys
from pathlib import Path

# Ensure backend is on the path for all tests
sys.path.insert(0, str(Path(__file__).parent / "backend"))
