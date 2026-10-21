#!/bin/bash

cd "$(dirname "$0")"
./.venv/bin/python3 mp4_to_ascii.py

read -p "Press Enter to exit..."