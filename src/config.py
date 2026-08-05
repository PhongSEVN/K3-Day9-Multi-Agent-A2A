"""Runtime configuration for the EC dispute-resolution multi-agent pipeline."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
LOGGING_DIR = ROOT_DIR / "logging"
TRACE_PATH = LOGGING_DIR / "trace.jsonl"
METADATA_PATH = LOGGING_DIR / "metadata.json"

# Model name is hardcoded here per submission rules (never read from .env).
# OpenAI does not publish parameter counts for this model; instructor
# explicitly approved use of an OpenAI "mini" tier model for this lab
# despite the undisclosed size, in place of the local <=10B Ollama models.
# Chosen over local qwen2.5:3b for turnaround speed on a 50-case run; safe
# either way because every decision field comes from the deterministic
# rule engine (policy_rules.py) — the LLM only produces logged narration.
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_MODEL_PARAM_NOTE = (
    "undisclosed by OpenAI (closed-weight); instructor-approved substitute "
    "for the assignment's <=10B local-model requirement"
)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Kept only so a local fallback can be re-enabled quickly if needed.
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_MODEL_PARAM_NOTE = "3B parameters (Qwen2.5 3B, Alibaba, open-weight)"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

POLICY_VERSION = "EC_POLICY_V1"
CURRENCY = "BRL"
AMOUNT_TOLERANCE_BRL = 0.10

MAX_ENTITY_IDS = 5
MAX_EVIDENCE_IDS = 10
MAX_ROOT_CAUSES = 3
MAX_RESPONSIBLE_PARTIES = 3
MAX_RESOLUTION_ACTIONS = 5
