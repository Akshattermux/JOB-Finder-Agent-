#!/usr/bin/env bash

# Activate virtual environment if present
if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Run main interactive menu
python main.py
