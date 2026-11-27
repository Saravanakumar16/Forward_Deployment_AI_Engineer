"""Run the whole lab end to end and refresh the README with the results.

    python run_all.py
Equivalent to: bootstrap.py -> ingest.py -> compare_chunking.py -> exercise_d.py
               -> test_security.py -> scripts/update_readme.py
"""
import subprocess, sys

STEPS = ["bootstrap.py", "ingest.py", "compare_chunking.py", "exercise_d.py", "test_security.py",
         "scripts/update_readme.py"]

for step in STEPS:
    print(f"\n===== python {step} =====", flush=True)
    rc = subprocess.call([sys.executable, step])
    if rc:
        sys.exit(f"{step} failed with exit code {rc}")
print("\nAll steps completed. Evidence is in results/ and README.md has been refreshed.")
