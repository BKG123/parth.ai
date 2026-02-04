"""Parth.ai - Main entry point."""

import subprocess
import sys


def main():
    """Launch the Streamlit app."""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app_streamlit.py",
            "--logger.level=debug",
        ]
    )


if __name__ == "__main__":
    main()
