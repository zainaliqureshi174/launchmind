"""
main.py
-------
Entry point for the LaunchMind Multi-Agent System.
Run this file to launch the entire agent pipeline.

Usage:
    python main.py
    python main.py "Your custom startup idea here"
"""

import sys
from agents.ceo_agent import run as run_ceo

# ── Default startup idea — change this to your own! ──
DEFAULT_IDEA = (
    "A mobile platform where university students can buy and sell "
    "second-hand textbooks, with AI-powered price suggestions and "
    "instant campus-to-campus delivery coordination."
)


def main():
    # Allow passing a custom idea via command line
    if len(sys.argv) > 1:
        idea = " ".join(sys.argv[1:])
    else:
        idea = DEFAULT_IDEA

    print("\n" + "🚀 " * 20)
    print("  LAUNCHMIND MULTI-AGENT SYSTEM")
    print("🚀 " * 20)
    print(f"\nStartup Idea:\n  {idea}\n")

    # Hand off to the CEO agent — it orchestrates everything from here
    run_ceo(idea)


if __name__ == "__main__":
    main()