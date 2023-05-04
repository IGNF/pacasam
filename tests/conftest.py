# Add the src subdir to have simple import in the test suite
# e.g. "import pacasam" instead of "import src.pacasam"
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir / "src"))
