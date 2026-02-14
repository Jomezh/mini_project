#!/bin/bash
# Setup script for ILI9341 display on Raspberry Pi Zero 2W

echo "Setting up ILI9341 display..."

# Install fbcp for framebuffer copy
cd ~
git clone https://github.com/juj/fbcp-ili9341.git
cd fbcp-ili9341
mkdir build
cd build

# Configure for ILI9341
cmake -DILI9341=ON -DGPIO_TFT_DATA_CONTROL=24 -DGPIO_TFT_RESET_PIN=25 \
      -DSPI_BUS_CLOCK_DIVISOR=6 -DSTATISTICS=0 ..

make -j
sudo ./fbcp-ili9341 &

echo "Display setup complete!"
