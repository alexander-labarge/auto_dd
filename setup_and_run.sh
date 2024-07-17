#!/bin/bash

# Ensure we're running as root for parts that need it
if [ "$EUID" -ne 0 ]; then
  echo "This script needs to install packages and create files as root."
  echo "Please enter your password to proceed."
  sudo "$0"
  exit $?
fi

# Install Python 3 and pip if they are not already installed
if ! command -v python3 &> /dev/null; then
  echo "Installing Python 3..."
  apt-get update
  apt-get install -y python3
fi

if ! command -v pip3 &> /dev/null; then
  echo "Installing pip for Python 3..."
  apt-get install -y python3-pip
fi

# Install python3-venv if it's not installed
if ! dpkg -l | grep -q python3-venv; then
  echo "Installing python3-venv..."
  apt-get install -y python3-venv
fi

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# Activate the virtual environment and install required packages
echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing required packages..."
pip install -r requirements.txt

# Provide information on how to activate the virtual environment manually
echo "Setup Complete. To run the script, use the following command after activating the virtual environment:"
echo "source venv/bin/activate"
echo "sudo venv/bin/python3.12 auto_dd.py --help"

# Activate the virtual environment
source venv/bin/activate
sudo venv/bin/python3.12 auto_dd.py --help
