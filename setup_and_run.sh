#!/bin/bash

# Ensure we're running as root for parts that need it
if [ "$EUID" -ne 0 ]; then
  echo "This script needs to install packages and create files as root."
  echo "Please enter your password to proceed."
  sudo "$0"
  exit $?
fi

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  sudo -u "$USER" python3 -m venv venv
fi

# Activate the virtual environment and install required packages
echo "Activating virtual environment..."
sudo -u "$USER" bash -c "source venv/bin/activate && pip install -r requirements.txt"

# Provide information on how to activate the virtual environment manually
echo "Setup Complete. To run the script, use the following command after activating the virtual environment:"
echo "source venv/bin/activate"
echo "sudo venv/bin/python3.12 auto_dd.py --help"
source venv/bin/activate
sudo venv/bin/python3.12 auto_dd.py --help