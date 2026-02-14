#!/bin/bash
# Installation script for MiniK system

echo "Installing MiniK VOC Detection System..."

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libportmidi-dev \
    libswscale-dev \
    libavformat-dev \
    libavcodec-dev \
    zlib1g-dev \
    libgstreamer1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    git \
    i2c-tools \
    python3-smbus \
    bluez \
    bluez-tools \
    python3-dbus

# Enable I2C and SPI
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_camera 0

# Install Python packages
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Create necessary directories
mkdir -p ~/python_app/captures
mkdir -p ~/python_app/data
mkdir -p ~/python_app/logs

# Set permissions
chmod +x setup_display.sh
chmod +x run.sh

echo "Installation complete!"
echo "Please reboot the system: sudo reboot"
