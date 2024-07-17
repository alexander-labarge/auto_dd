#!/bin/bash

source venv/bin/activate
sudo venv/bin/python3.12 auto_dd.py --source /dev/nvme0n1 --destination /dev/sda --benchmark --benchmark-size 4096

# sudo venv/bin/python3.12 auto_dd.py --source /dev/nvme0n1 --destination /dev/sda --enable-service --start-service --block-size 32768
