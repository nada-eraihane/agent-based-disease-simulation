#!/usr/bin/env python3
"""Launch the Hospital Infection Simulation."""
import subprocess, sys

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "solara", "run", "hospital_sim_v2.app", "--port", "8765"])