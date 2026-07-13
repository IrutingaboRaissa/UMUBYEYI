"""Make src/ importable for the test suite."""
import os
import sys

os.environ["UMU_DISABLE_OLLAMA"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
