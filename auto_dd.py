"""
Auto DD Script: Automate the dd command with benchmarking and systemd service setup.
"""

import argparse
import os
import subprocess
import re
import sys
import time
import pandas as pd

def usage():
    """Prints the usage information for the script and exits."""
    print("""
Usage: auto_dd.py [--source <SOURCE_DRIVE>] [--destination <DEST_DRIVE>] [--block-size <BLOCK_SIZE>]
                 [--benchmark-size <SIZE>] [--start-now] [--benchmark] [--enable-service] [--start-service]
  --source <SOURCE_DRIVE>        Specify the source drive (default: /dev/nvme0n1)
  --destination <DEST_DRIVE>     Specify the destination drive (default: /dev/sdb)
  --block-size <BLOCK_SIZE>      Specify the block size for dd command (default: 32768)
  --benchmark-size <SIZE>        Specify the size of the benchmark in MB (default: 512 MB)
  --start-now                    Start the dd command immediately after setup
  --benchmark                    Benchmark to determine the best block size
  --enable-service               Enable the systemd service
  --start-service                Start the systemd service

The dd command used in this program:
  dd if=<SOURCE_DRIVE> of=<DEST_DRIVE> bs=<BLOCK_SIZE> seek=0 count=<COUNT> status=progress [conv=fsync]

Flags explanation:
  if: Input file (source drive)
  of: Output file (destination drive)
  bs: Block size for read/write operations
  seek=0: Start writing at byte offset 0
  count=<COUNT>: Limit the number of blocks to copy
  status=progress: Display the progress of the operation
  conv=fsync: Physically write data to disk before finishing (not used for /dev/null)

Reason for block size 32768:
  The block size of 32768 bytes (32 KB) is often a good balance between performance and system resource usage.
  It can reduce the number of I/O operations by increasing the amount of data read/written per operation,
  which can improve overall throughput for large data transfers.

To view the output of the dd system service after boot, run the following command:
  sudo journalctl -u auto_dd.service -f
    """)
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

def flush_and_repartition(dest_drive):
    """Creates a new GPT partition table."""
    try:
        subprocess.run(["sgdisk", "--zap-all", dest_drive], check=True)
        subprocess.run(["sgdisk", "--new=1:0:0", dest_drive], check=True)
        subprocess.run(["partprobe", dest_drive], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error repartitioning {dest_drive}: {e}")
        return False
    return True

def run_dd(source_drive, dest_drive, block_size, benchmark_size):
    """Runs the dd command and returns the duration and output file."""
    count = (benchmark_size * 1024 * 1024) // block_size
    output_file = f"dd_output_{block_size}.txt"
    command = [
        "dd",
        f"if={source_drive}",
        f"of={dest_drive}",
        f"bs={block_size}",
        f"count={count}",
        "seek=0",
        "status=progress"
    ]

    if dest_drive != "/dev/null":
        command.append("conv=fsync")

    if not flush_and_repartition(dest_drive):
        return None, None

    with open(output_file, "w", encoding="utf-8") as f:
        start_time = time.time()
        try:
            subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, timeout=300, check=True)
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
    raise ValueError(f"Could not parse speed from {output_file}")

def benchmark(source_drive, dest_drive, benchmark_size):
    """Benchmarks different block sizes to determine the best one."""
    block_sizes = [
        512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288,
        1048576, 2097152, 4194304, 8388608, 16777216, 33554432, 67108864, 10485760
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
    print(df.to_string(index=False))

    print(f"Best block size determined: {format_block_size(best_block_size)} "
          f"with speed: {best_speed:.2f} MB/s")
    return best_block_size

def create_dd_script(source_drive, dest_drive, block_size):
    """Creates the dd script to be run by the systemd service."""
    script_content = f"""#!/bin/bash
dd if={source_drive} of={dest_drive} bs={block_size} seek=0 status=progress conv=fsync
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
    with open("/etc/systemd/system/auto_dd.service", "w", encoding="utf-8") as f:
        f.write(service_content)

    subprocess.run(["systemctl", "daemon-reload"], check=True)

def enable_systemd_service():
    """Enables the systemd service."""
    subprocess.run(["systemctl", "enable", "auto_dd.service"], check=True)

def start_systemd_service():
    """Starts the systemd service."""
    subprocess.run(["systemctl", "start", "auto_dd.service"], check=True)

def main():
    """Main function to parse arguments and execute the appropriate actions."""
    parser = argparse.ArgumentParser(description="Auto dd script")
    parser.add_argument("--source", default="/dev/nvme0n1",
                        help="Specify the source drive (default: /dev/nvme0n1)")
    parser.add_argument("--destination", default="/dev/sdb",
                        help="Specify the destination drive (default: /dev/sdb)")
    parser.add_argument("--block-size", type=int, default=32768,
                        help="Specify the block size for dd command (default: 32768)")
    parser.add_argument("--benchmark-size", type=int, default=512,
                        help="Specify the size of the benchmark in MB (default: 512 MB)")
    parser.add_argument("--start-now", action="store_true",
                        help="Start the dd command immediately after setup")
    parser.add_argument("--benchmark", action="store_true",
                        help="Benchmark to determine the best block size")
    parser.add_argument("--enable-service", action="store_true",
                        help="Enable the systemd service")
    parser.add_argument("--start-service", action="store_true",
                        help="Start the systemd service")

    args = parser.parse_args()

    if args.benchmark:
        print("Benchmarking to determine the best block size...")
        args.block_size = benchmark(args.source, args.destination, args.benchmark_size)

    create_dd_script(args.source, args.destination, args.block_size)

    if args.start_now:
        print("Starting the dd command immediately...")
        subprocess.run(["/usr/local/bin/run_dd.sh"], check=True)
        sys.exit(0)

    create_systemd_service()

    if args.enable_service:
        enable_systemd_service()

    if args.start_service:
        start_systemd_service()

    print("Setup complete. The dd command will now run on startup.")
    print("To view the output of the dd system service after boot, run the following command:")
    print("  sudo journalctl -u auto_dd.service -f")

if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.stderr.write("This program must be run as root.\n")
        sys.exit(1)
    main()
