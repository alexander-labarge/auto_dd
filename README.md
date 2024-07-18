# darthdd

`darthdd` is a Python driven program designed to automate the benchmarking and usage of the `dd` linux utility to determine the best block size for most performant data transfer/ drive duplication operations. It also includes functionality to enable and start the `dd` operation as a systemd service on system startup to facilitate automated backups or automatic drive duplication efforts. 

## Prerequisites

- Python 3.12
- `venv` module for creating virtual environments
- `pip` for installing required packages
- Tested on Ubuntu 24.04

## Installation

1. Clone the repository:

   ```sh
   git clone https://github.com/alexander-labarge/darthdd.git
   cd darthdd/
   ```

2. Create and activate a virtual environment:

   ```sh
   python3.12 -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:

   ```sh
   pip install -r requirements.txt
   ```

## Usage

After setting up, you can run the script with various arguments to perform different operations. Here is a list of available arguments:

```sh
usage: darthdd.py [-h] [--source SOURCE] [--destination DESTINATION] [--block-size BLOCK_SIZE] [--benchmark-size BENCHMARK_SIZE] [--execute-with-autobench] [--benchmark] [--enable-service] [--start-service]

Auto dd script

Arguments:
  -h, --help            show this help message and exit
  --source SOURCE       Specify the source drive (default: /dev/nvme0n1)
  --destination DESTINATION
                        Specify the destination drive (default: /dev/sda)
  --block-size BLOCK_SIZE
                        Specify the block size for dd command (default: 32768)
  --benchmark-size BENCHMARK_SIZE
                        Specify the size of the benchmark in MB (default: 1024 MB)
  --execute-with-autobench
                        Run benchmark and start the dd command with the best block size
  --benchmark           Benchmark to determine the best block size
  --enable-service      Enable the systemd service
  --start-service       Start the systemd service
```

### Example Commands

#### Run benchmark and start `dd` with the best block size:

```sh
# Description: Run benchmark with default 1024 MB size and start dd with the best block size
sudo venv/bin/python3.12 darthdd.py --execute-with-autobench --source /dev/nvme0n1 --destination /dev/sda
```

#### Benchmark to determine the best block size:

```sh
# Description: Run benchmark to determine the best block size
sudo venv/bin/python3.12 darthdd.py --benchmark --source /dev/nvme0n1 --destination /dev/sda
```

#### Enable the systemd service:

```sh
# Description: Enable the systemd service for auto_dd
sudo venv/bin/python3.12 darthdd.py --enable-service
```

#### Start the systemd service:

```sh
# Description: Start the systemd service for auto_dd
sudo venv/bin/python3.12 darthdd.py --start-service
```

## Systemd Service

The script can enable and start a systemd service that runs the `dd` command on system startup. Use the `--enable-service` and `--start-service` arguments to enable and start the service.

### Viewing Service Logs

To view the output of the `dd` system service after boot, run:

```sh
sudo journalctl -u darthdd.service -f
```

## Contributing

If you have any suggestions or improvements, feel free to open an issue or create a pull request.

## License

This project is licensed under the MIT License.

---