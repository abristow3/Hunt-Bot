#!/usr/bin/env python3
import sys
import os

# Sets the project root to /Hunt-Bot instead of /Hunt-Bot/bin since we run the bot from /bin
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from huntbot.main import run

if __name__ == "__main__":
    run()
