#!/bin/bash
# Run script for MiniK application

# Set environment variables
export KIVY_WINDOW=sdl2
export KIVY_GL_BACKEND=sdl2

# Set display for SPI screen (if using fbcp)
export DISPLAY=:0

# Run the application
cd ~/python_app
python3 main.py 2>&1 | tee logs/app_$(date +%Y%m%d_%H%M%S).log
