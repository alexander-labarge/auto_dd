# auto_dd

`auto_dd` is a Python script designed to automate the benchmarking and usage of the `dd` command to determine the best block size for data transfer operations. It also includes functionality to enable and start the `dd` operation as a systemd service on system startup.

## Prerequisites

- Python 3.12
- `venv` module for creating virtual environments
- `pip` for installing required packages
- Tested on Ubuntu 24.04

## Installation

1. Clone the repository:

   ```sh
   git clone https://github.com/alexander-labarge/auto_dd.git
   cd auto_dd/
   ```

2. Run the setup script:

   ```sh
   ./setup_and_run.sh
   ```

3. To benchmark and determine the best block size, run:

   ```sh
   sudo ./benchmark.sh
   ```

## Usage

After setting up, you can run the script with various arguments to perform different operations. Here is a list of available arguments:

```sh
usage: auto_dd.py [-h] [--source SOURCE] [--destination DESTINATION] [--block-size BLOCK_SIZE] [--benchmark-size BENCHMARK_SIZE] [--start-now] [--benchmark]
                  [--enable-service] [--start-service]

Auto dd script

options:
  -h, --help            show this help message and exit
  --source SOURCE       Specify the source drive (default: /dev/nvme0n1)
  --destination DESTINATION
                        Specify the destination drive (default: /dev/sdb)
  --block-size BLOCK_SIZE
                        Specify the block size for dd command (default: 32768)
  --benchmark-size BENCHMARK_SIZE
                        Specify the size of the benchmark in MB (default: 1024 MB)
  --start-now           Start the dd command immediately after setup
  --benchmark           Benchmark to determine the best block size
  --enable-service      Enable the systemd service
  --start-service       Start the systemd service
```

### Example Commands

To benchmark and determine the best block size:

```sh
source venv/bin/activate
sudo venv/bin/python3.12 auto_dd.py --source /dev/nvme0n1 --destination /dev/sda --benchmark --benchmark-size 1024 --enable-service
```

To execute the service immediately with the best block size:

```sh
source venv/bin/activate
sudo venv/bin/python3.12 auto_dd.py --source /dev/nvme0n1 --destination /dev/sda --enable-service --start-service --benchmark --benchmark-size 1024
```

To allow the benchmark in conjunction with `--start-service` to automatically select the best block size and start the copy:

```sh
source venv/bin/activate
sudo venv/bin/python3.12 auto_dd.py --source /dev/nvme0n1 --destination /dev/sda --benchmark --benchmark-size 1024 --enable-service --start-service
```

## Systemd Service

The script can enable and start a systemd service that runs the `dd` command on system startup. Use the `--enable-service` and `--start-service` arguments to enable and start the service.

### Viewing Service Logs

To view the output of the `dd` system service after boot, run:

```sh
sudo journalctl -u auto_dd.service -f
```

## Contributing

If you have any suggestions or improvements, feel free to open an issue or create a pull request.

## License

This project is licensed under the MIT License.
