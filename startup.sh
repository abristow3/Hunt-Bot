#!/bin/bash
source .venv/bin/activate
pip install -r requirements.txt
nohup python3 main.py &