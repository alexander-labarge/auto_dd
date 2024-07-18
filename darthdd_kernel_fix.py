import argparse
import os
import subprocess
import re
import sys
import time
import pandas as pd
from tabulate import tabulate
from termcolor import colored

def usage():
    """Prints the usage information for the script and exits."""
    ascii_art = """
M\"\"\"\"\"\"'YMM                     dP   dP       M\"\"\"\"\"\"'YMM M\"\"\"\"\"\"'YMM 
M  mmmm. `M                     88   88       M  mmmm. `M M  mmmm. `M 
M  MMMMM  M .d8888b. 88d888b. d8888P 88d888b. M  MMMMM  M M  MMMMM  M 
M  MMMMM  M 88'  `88 88'  `88   88   88'  `88 M  MMMMM  M M  MMMMM  M 
M  MMMM' .M 88.  .88 88         88   88    88 M  MMMM' .M M  MMMM' .M 
M       .MM `88888P8 dP         dP   dP    dP M       .MM M       .MM 
MMMMMMMMMMM                                   MMMMMMMMMMM MMMMMMMMMMM 
                                                                      
"""

    print(colored(ascii_art, 'red'))

    help_data = [
        ["Arguments", "Description"],
        ["--source <SOURCE_DRIVE>", "Specify the source drive (default: /dev/nvme0n1)"],
        ["--destination <DEST_DRIVE>", "Specify the destination drive (default: /dev/sdb)"],
        ["--block-size <BLOCK_SIZE>", "Specify the block size for dd command (default: 32768)"],
        ["--benchmark-size <SIZE>", "Specify the size of the benchmark in MB (default: 1024 MB)"],
        ["--execute-with-autobench", "Run benchmark and start the dd command with the best block size"],
        ["--benchmark", "Benchmark to determine the best block size"],
        ["--enable-service", "Enable the systemd service"],
        ["--start-service", "Start the systemd service"],
    ]

    command_data = [
        ["Benchmark Command Utilized"],
        ["dd if=<SOURCE_DRIVE> of=<DEST_DRIVE> bs=<BLOCK_SIZE> seek=<SEEK_VALUE> count=<COUNT> status=progress"],
    ]

    flags_data = [
        ["Flag", "Explanation"],
        ["if", "Input file (source drive)"],
        ["of", "Output file (destination drive)"],
        ["bs", "Block size for read/write operations"],
        ["seek=<SEEK_VALUE>", "Start writing at byte offset 4MB"],
        ["count=<COUNT>", "Limit the number of blocks to copy"],
        ["status=progress", "Display the progress of the operation"]
    ]

    example_commands = [
        ["Example Commands"],
        ["Run benchmark and start dd with best block size"],
        ["sudo venv/bin/python3.12 auto_dd.py --execute-with-autobench --source /dev/nvme0n1 --destination /dev/sda"],
        ["Benchmark to determine best block size"],
        ["sudo venv/bin/python3.12 auto_dd.py --benchmark --source /dev/nvme0n1 --destination /dev/sda"],
        ["Enable the systemd service"],
        ["sudo venv/bin/python3.12 auto_dd.py --enable-service"],
        ["Start the systemd service"],
        ["sudo venv/bin/python3.12 auto_dd.py --start-service"]
    ]

    print(colored(tabulate(help_data, headers="firstrow", tablefmt="fancy_grid"), 'yellow'))
    print(colored(tabulate(command_data, headers="firstrow", tablefmt="fancy_grid"), 'blue'))
    print(colored(tabulate(flags_data, headers="firstrow", tablefmt="fancy_grid"), 'magenta'))

    for i in range(1, len(example_commands), 2):
        print(colored(example_commands[i][0], 'yellow'))
        print(colored(example_commands[i + 1][0], 'green'))

    sys.exit(1)

def format_block_size(bs):
    """Formats the block size into a human-readable string."""
    if bs >= 1024**3:
        return f"{bs / 1024**3:.2f} GB"
    if bs >= 1024**2:
        return f"{bs / 1024**2:.2f} MB"
    if bs >= 1024:
        return f"{bs / 1024:.2f} KB"
    return f"{bs} bytes"

def flush_cache():
    """Flushes the OS buffer cache."""
    try:
        subprocess.run(["sync"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error flushing cache: {e}")

def clear_destination(dest_drive):
    """Clears the destination device by writing zeros to it."""
    clear_command = [
        "dd",
        "if=/dev/zero",
        f"of={dest_drive}",
        "bs=1M",
        "status=progress",
        "conv=fsync"
    ]
    try:
        subprocess.run(clear_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error clearing destination device {dest_drive}: {e}")

def run_dd(source_drive, dest_drive, block_size, benchmark_size):
    """Runs the dd command and returns the duration and output file."""
    count = (benchmark_size * 1024 * 1024) // block_size
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)
    output_file = os.path.join(results_dir, f"dd_output_{block_size}.txt")
    command = [
        "dd",
        f"if={source_drive}",
        f"of={dest_drive}",
        f"bs={block_size}",
        f"count={count}",
        "status=progress",
        "conv=fsync"
    ]

    flush_cache()
    clear_destination(dest_drive)

    with open(output_file, "w", encoding="utf-8") as f:
        start_time = time.time()
        try:
            subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, timeout=1800, check=True)
        except subprocess.TimeoutExpired:
            return None, output_file
        except subprocess.CalledProcessError as e:
            if "No space left on device" in str(e):
                print(f"Error: {e}. Reducing benchmark size might help.")
            return None, output_file
        end_time = time.time()

    return end_time - start_time, output_file

def parse_speed(output_file):
    """Parses the speed from the dd output file."""
    with open(output_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    last_line = lines[-1].strip()

    match = re.search(r"(\d+) bytes .* copied, ([\d.]+) s, ([\d.]+ .B/s)", last_line)
    if match:
        bytes_transferred = int(match.group(1))
        time_seconds = float(match.group(2))
        speed = match.group(3)
        return time_seconds, speed, bytes_transferred
    raise ValueError

def benchmark(source_drive, dest_drive, benchmark_size):
    """Benchmarks different block sizes to determine the best one."""
    block_sizes = [
        512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288,
        1048576, 2097152, 4194304, 8388608, 16777216, 33554432, 67108864
    ]
    results = []
    best_speed = 0
    best_block_size = 32768

    for bs in block_sizes:
        duration, output_file = run_dd(source_drive, dest_drive, bs, benchmark_size)
        if duration is None:
            results.append((format_block_size(bs), None, None, None))
            continue
        try:
            time_seconds, speed, bytes_transferred = parse_speed(output_file)
            mb_transferred = bytes_transferred / (1024 * 1024)
            gb_transferred = bytes_transferred / (1024**3)
            speed_value, speed_unit = speed.split()
            speed_value = float(speed_value)
            if "GB" in speed_unit:
                speed_value *= 1024  # Convert GB/s to MB/s
            results.append(
                (format_block_size(bs),
                 f"{mb_transferred:.2f} MB / {gb_transferred:.2f} GB",
                 time_seconds, speed)
            )
            if speed_value > best_speed:
                best_speed = speed_value
                best_block_size = bs
        except (ValueError, IndexError):
            results.append((format_block_size(bs), None, None, None))
            continue

    df = pd.DataFrame(results, columns=["Block Size", "Data Transferred", "Time (seconds)", "Speed"])
    table = tabulate(df, headers='keys', tablefmt='fancy_grid')
    print(colored(table, 'cyan'))

    print(colored(f"Best block size determined: {format_block_size(best_block_size)} with speed: {best_speed:.2f} MB/s", 'green'))
    return best_block_size

def execute_with_autobench(source_drive, dest_drive):
    """Executes the benchmark with default 1024 MB size and starts the dd command with the best block size."""
    print(colored("Running benchmark with default 1024 MB size...", 'yellow'))
    best_block_size = benchmark(source_drive, dest_drive, 1024)
    print(colored(f"Starting the dd command with the best block size: {best_block_size}", 'yellow'))
    run_dd(source_drive, dest_drive, best_block_size, 1024)
    print(colored("Copy operation completed.", 'green'))

def create_dd_script(source_drive, dest_drive, block_size):
    """Creates the dd script to be run by the systemd service."""
    script_content = f"""#!/bin/bash
dd if={source_drive} of={dest_drive} bs={block_size} seek=8192 status=progress conv=fsync
"""
    with open("/usr/local/bin/run_dd.sh", "w", encoding="utf-8") as f:
        f.write(script_content)
    os.chmod("/usr/local/bin/run_dd.sh", 0o755)

def create_systemd_service():
    """Creates the systemd service file."""
    service_content = """[Unit]
Description=Run dd command at startup
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/run_dd.sh
Restart=on-failure
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    with open("/etc/systemd/system/darthdd.service", "w", encoding="utf-8") as f:
        f.write(service_content)

    subprocess.run(["systemctl", "daemon-reload"], check=True)

def enable_systemd_service():
    """Enables the systemd service."""
    subprocess.run(["systemctl", "enable", "darthdd.service"], check=True)

def start_systemd_service():
    """Starts the systemd service."""
    subprocess.run(["systemctl", "start", "darthdd.service"], check=True)

class CustomArgumentParser(argparse.ArgumentParser):
    def print_help(self):
        usage()

def main():
    """Main function to parse arguments and execute the appropriate actions."""
    parser = CustomArgumentParser(description="Auto dd script")
    parser.add_argument("--source", default="/dev/nvme0n1",
                        help="Specify the source drive (default: /dev/nvme0n1)")
    parser.add_argument("--destination", default="/dev/sda",
                        help="Specify the destination drive (default: /dev/sda)")
    parser.add_argument("--block-size", type=int, default=32768,
                        help="Specify the block size for dd command (default: 32768)")
    parser.add_argument("--benchmark-size", type=int, default=1024,
                        help="Specify the size of the benchmark in MB (default: 1024 MB)")
    parser.add_argument("--execute-with-autobench", action="store_true",
                        help="Run benchmark and start the dd command with the best block size")
    parser.add_argument("--benchmark", action="store_true",
                        help="Benchmark to determine the best block size")
    parser.add_argument("--enable-service", action="store_true",
                        help="Enable the systemd service")
    parser.add_argument("--start-service", action="store_true",
                        help="Start the systemd service")
    args = parser.parse_args()

    if args.execute_with_autobench:
        execute_with_autobench(args.source, args.destination)
        sys.exit(0)

    if args.benchmark:
        print(colored("Benchmarking to determine the best block size...", 'yellow'))
        args.block_size = benchmark(args.source, args.destination, args.benchmark_size)

    create_dd_script(args.source, args.destination, args.block_size)

    create_systemd_service()

    if args.enable_service:
        enable_systemd_service()

    if args.start_service:
        start_systemd_service()

    print(colored("Setup complete. The dd command will now run on startup.", 'green'))
    print(colored("To view the output of the dd system service after boot, run the following command:", 'green'))
    print(colored("  sudo journalctl -u darthdd.service -f", 'cyan'))

if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.stderr.write(colored("This program must be run as root.\n", 'red'))
        sys.exit(1)
    main()