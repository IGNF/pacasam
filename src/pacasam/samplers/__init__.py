import sys
from pathlib import Path

directory = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(directory))
