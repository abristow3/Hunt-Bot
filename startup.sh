#!/bin/bash
cd /opt/bots/Hunt-Bot
python3 -m venv .venv
source .venv/bin/active
pip install -r requirements.txt
nohup python3 main.py &