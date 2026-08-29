import os
import sys

# Ensure root directory is in Python path for direct 'pytest tests/ -v' invocation
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
