#!/bin/bash

# This script is for installing the dependencies for the HandGhost project.

# It is recommended to use a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
