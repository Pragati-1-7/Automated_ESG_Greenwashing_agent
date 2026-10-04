"""
main.py

Placeholder entry point for the ESG Greenwashing Detection & Verification Agent.

STATUS: Step 1 (repository + dataset foundation) is complete.
The extraction -> retrieval -> evaluation -> scoring pipeline and the
FastAPI/Streamlit application described in the project plan are NOT
implemented yet. This file exists so the project has a single obvious
entry point that will be wired up to the real pipeline in later phases.

For now, running this file simply confirms the project is set up
correctly by running the dataset validator.
"""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    print("ESG Greenwashing Detection & Verification Agent")
    print("Status: Step 1 complete (repository structure + dataset foundation).")
    print("The verification pipeline (extraction, retrieval, scoring, API, UI) is not implemented yet.\n")
    print("Running the dataset validator as a sanity check...\n")

    script = Path(__file__).parent / "scripts" / "validate_dataset.py"
    result = subprocess.run([sys.executable, str(script)])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
