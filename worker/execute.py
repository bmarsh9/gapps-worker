import sys
import json

# argv[1] = config path
# argv[2] = result path
# argv[3] = repo root (for utils and config)

with open(sys.argv[1], "r") as f:
    config = json.load(f)

# Add repo root so utils and config are importable
sys.path.insert(0, sys.argv[3])

# Add integration directory so entry.py is importable
sys.path.insert(0, sys.argv[4])

from entry import Runner

runner = Runner(config)
result = runner.run()

with open(sys.argv[2], "w") as f:
    json.dump(result, f)