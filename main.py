"""Parth.ai - Main entry point."""

import subprocess
import sys


def main():
    """Launch the Streamlit app."""
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app_streamlit.py"])


if __name__ == "__main__":
    main()
