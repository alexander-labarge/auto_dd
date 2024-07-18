#!/bin/bash

# Global variables
initial_device="/dev/sda"
source_device="/dev/nvme0n1"
block_size=1M
data_size=10G

# Convert data size to number of blocks (assuming data_size is in GB and block_size is 1M)
data_size_in_mb=$(echo $data_size | sed 's/[A-Za-z]//g')
num_blocks=$((data_size_in_mb * 1024))
num_bytes=$((data_size_in_mb * 1024 * 1024))

# Function to zero out the first and last 1 MB of the drive
zero_out_drive() {
  local drive=$1

  echo "Zeroing out the first 1 MB of $drive..."
  sudo dd if=/dev/zero of=$drive bs=1M count=1 status=progress
  echo "First 1 MB zeroed out."

  local drive_size=$(sudo blockdev --getsize64 $drive)
  if [ $? -ne 0 ]; then
    echo "Error getting the size of $drive. Exiting."
    exit 1
  fi
  local seek_value=$((drive_size / 1048576 - 1))

  echo "Zeroing out the last 1 MB of $drive at seek=$seek_value..."
  sudo dd if=/dev/zero of=$drive bs=1M seek=$seek_value count=1 status=progress
  echo "Last 1 MB zeroed out."
}

# Function to partition and format the drive
prepare_drive() {
  local drive=$1
  local partition_size=$2

  echo "Preparing the drive $drive..."

  # Unmount any existing partitions
  sudo umount ${drive}* || true

  # Remove all partitions
  echo "Removing all partitions on $drive..."
  echo -e "d\nn\np\n1\n\n+${partition_size}\nw" | sudo fdisk $drive

  # Reinitialize the USB device
  echo "Reinitializing the USB device..."
  echo 1 | sudo tee /sys/block/$(basename $drive)/device/delete
  sleep 1
  for usb in $(ls /sys/bus/usb/drivers/usb/ | grep 'usb[0-9]$'); do
    echo -n "$usb" | sudo tee /sys/bus/usb/drivers/usb/unbind
    sleep 1
    echo -n "$usb" | sudo tee /sys/bus/usb/drivers/usb/bind
  done
  
  sleep 5
  
  # Create the filesystem
  echo "Creating filesystem on ${drive}1..."
  sudo mkfs.ext4 ${drive}1

  echo "Drive $drive prepared."
}

# Function to flush the OS buffer cache
flush_cache() {
  echo "Flushing OS buffer cache..."
  sync
  echo 3 | sudo tee /proc/sys/vm/drop_caches
  echo "Cache flush completed."
}

# Function to run the dd command
run_dd() {
  local source=$1
  local target=$2
  local bs=$3
  local count=$4

  echo "Running dd command with offset..."
  sudo dd if=$source of=${target}1 bs=$bs count=$count status=progress conv=fsync
  echo "dd command completed."
}

# Function to find the drive by WWID
find_drive_by_wwid() {
  local wwid=$1
  lsblk -o NAME,WWN | grep "$wwid" | awk '{print "/dev/" $1}'
}

# Function to get the WWID of the initial device
get_wwid() {
  local device=$1
  sudo lsblk -no WWN $device
}

# Main benchmark loop
for i in $(seq 1 10); do
  echo "Starting iteration $i..."
  echo "---------------------------------------"
  
  if [ -z "$usb_wwid" ]; then
    # Detect the WWID of the initial device
    usb_wwid=$(get_wwid $initial_device)
    if [ -z "$usb_wwid" ]; then
      echo "WWID of the initial device not found. Exiting."
      exit 1
    fi
    echo "Detected WWID of the USB device: $usb_wwid"
  fi

  # Detect the drive with the specified WWID
  target_device=$(find_drive_by_wwid "$usb_wwid")
  if [ -z "$target_device" ]; then
    echo "Drive with WWID $usb_wwid not found. Exiting."
    exit 1
  fi
  echo "Detected drive: $target_device"

  prepare_drive $target_device "${num_bytes}B"
  zero_out_drive ${target_device}1
  flush_cache
  run_dd $source_device $target_device $block_size $num_blocks
  flush_cache
  zero_out_drive ${target_device}1
  
  echo "Completed iteration $i."
  echo "======================================="
done
