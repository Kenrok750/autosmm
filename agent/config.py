import os
from dotenv import load_dotenv

load_dotenv()

# Base configurations
MAX_ITERATIONS = int(os.environ.get("MAX_ITERATIONS", 5))
HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "runs")
MIN_ACCEPTABLE_SCORE = float(os.environ.get("MIN_ACCEPTABLE_SCORE", 8.0))
