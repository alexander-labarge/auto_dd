#!/home/skywalker/venv/bin/python3.12

import argparse
import os
import subprocess
import re
import sys
import time
import pandas as pd

def usage():
    print("""
Usage: auto_dd.py [--source <SOURCE_DRIVE>] [--destination <DEST_DRIVE>] [--block-size <BLOCK_SIZE>] [--benchmark-size <SIZE>] [--start-now] [--benchmark] [--enable-service] [--start-service]
  --source <SOURCE_DRIVE>        Specify the source drive (default: /dev/nvme0n1)
  --destination <DEST_DRIVE>     Specify the destination drive (default: /dev/sdb)
  --block-size <BLOCK_SIZE>      Specify the block size for dd command (default: 32768)
  --benchmark-size <SIZE>        Specify the size of the benchmark in MB (default: 1024 MB)
  --start-now                    Start the dd command immediately after setup
  --benchmark                    Benchmark to determine the best block size
  --enable-service               Enable the systemd service
  --start-service                Start the systemd service

The dd command used in this program:
  dd if=<SOURCE_DRIVE> of=<DEST_DRIVE> bs=<BLOCK_SIZE> status=progress [conv=fsync]
Flags explanation:
  if: Input file (source drive)
  of: Output file (destination drive)
  bs: Block size for read/write operations
  status=progress: Display the progress of the operation
  conv=fsync: Physically write data to disk before finishing (not used for /dev/null)

Reason for block size 32768:
  The block size of 32768 bytes (32 KB) is often a good balance between performance and system resource usage. It can reduce the number of I/O operations by increasing the amount of data read/written per operation, which can improve overall throughput for large data transfers.

To view the output of the dd system service after boot, run the following command:
  sudo journalctl -u auto_dd.service -f
    """)
    sys.exit(1)

def format_block_size(bs):
    if bs >= 1024**3:
        return f"{bs / 1024**3:.2f} GB"
    elif bs >= 1024**2:
        return f"{bs / 1024**2:.2f} MB"
    elif bs >= 1024:
        return f"{bs / 1024:.2f} KB"
    else:
        return f"{bs} bytes"

def run_dd(source_drive, dest_drive, block_size, benchmark_size):
    count = (benchmark_size * 1024 * 1024) // block_size
    output_file = f"dd_output_{block_size}.txt"
    command = [
        "dd",
        f"if={source_drive}",
        f"of={dest_drive}",
        f"bs={block_size}",
        f"count={count}",
        "status=progress"
    ]

    if dest_drive != "/dev/null":
        command.append("conv=fsync")

    # Ensure the destination device is cleared before starting dd operation
    clear_command = [
        "sh",
        "-c",
        f"dd if=/dev/zero of={dest_drive} bs=1M count=1 conv=fsync"
    ]
    subprocess.run(clear_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    with open(output_file, "w") as f:
        start_time = time.time()
        try:
            subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, timeout=300)
        except subprocess.TimeoutExpired:
            return None, output_file
        except Exception as e:
            return None, output_file
        end_time = time.time()

    return end_time - start_time, output_file

def parse_speed(output_file):
    with open(output_file, "r") as f:
        lines = f.readlines()

    last_line = lines[-1].strip()

    match = re.search(r"(\d+) bytes .* copied, ([\d.]+) s, ([\d.]+ .B/s)", last_line)
    if match:
        bytes_transferred = int(match.group(1))
        time_seconds = float(match.group(2))
        speed = match.group(3)
        return time_seconds, speed, bytes_transferred
    else:
        raise ValueError(f"Could not parse speed from {output_file}")

def benchmark(source_drive, dest_drive, benchmark_size):
    block_sizes = [
        512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432, 67108864, 10485760
    ]
    results = []
    best_speed = 0
    best_block_size = 32768

    for bs in block_sizes:
        duration, output_file = run_dd(source_drive, dest_drive, bs, benchmark_size)
        if duration is None:
            results.append((format_block_size(bs), None, None, None, None))
            continue
        try:
            time, speed, bytes_transferred = parse_speed(output_file)
            mb_transferred = bytes_transferred / (1024 * 1024)
            gb_transferred = bytes_transferred / (1024**3)
            speed_value, speed_unit = speed.split()
            speed_value = float(speed_value)
            if "GB" in speed_unit:
                speed_value *= 1024  # Convert GB/s to MB/s
            results.append((format_block_size(bs), f"{mb_transferred:.2f} MB / {gb_transferred:.2f} GB", time, speed))
            if speed_value > best_speed:
                best_speed = speed_value
                best_block_size = bs
        except ValueError as e:
            results.append((format_block_size(bs), None, None, None, None))
            continue

    df = pd.DataFrame(results, columns=["Block Size", "Data Transferred", "Time (seconds)", "Speed"])
    print(df.to_string(index=False))

    print(f"Best block size determined: {format_block_size(best_block_size)} with speed: {best_speed:.2f} MB/s")
    return best_block_size

def create_dd_script(source_drive, dest_drive, block_size):
    script_content = f"""#!/bin/bash
dd if={source_drive} of={dest_drive} bs={block_size} status=progress conv=fsync
"""
    with open("/usr/local/bin/run_dd.sh", "w") as f:
        f.write(script_content)
    os.chmod("/usr/local/bin/run_dd.sh", 0o755)

def create_systemd_service():
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
    with open("/etc/systemd/system/auto_dd.service", "w") as f:
        f.write(service_content)

    subprocess.run(["systemctl", "daemon-reload"])

def enable_systemd_service():
    subprocess.run(["systemctl", "enable", "auto_dd.service"])

def start_systemd_service():
    subprocess.run(["systemctl", "start", "auto_dd.service"])

def main():
    parser = argparse.ArgumentParser(description="Auto dd script")
    parser.add_argument("--source", default="/dev/nvme0n1", help="Specify the source drive (default: /dev/nvme0n1)")
    parser.add_argument("--destination", default="/dev/sdb", help="Specify the destination drive (default: /dev/sdb)")
    parser.add_argument("--block-size", type=int, default=32768, help="Specify the block size for dd command (default: 32768)")
    parser.add_argument("--benchmark-size", type=int, default=1024, help="Specify the size of the benchmark in MB (default: 1024 MB)")
    parser.add_argument("--start-now", action="store_true", help="Start the dd command immediately after setup")
    parser.add_argument("--benchmark", action="store_true", help="Benchmark to determine the best block size")
    parser.add_argument("--enable-service", action="store_true", help="Enable the systemd service")
    parser.add_argument("--start-service", action="store_true", help="Start the systemd service")

    args = parser.parse_args()

    if args.benchmark:
        print("Benchmarking to determine the best block size...")
        args.block_size = benchmark(args.source, args.destination, args.benchmark_size)

    create_dd_script(args.source, args.destination, args.block_size)

    if args.start_now:
        print("Starting the dd command immediately...")
        subprocess.run(["/usr/local/bin/run_dd.sh"])
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
