#!/bin/bash
# Passenger restart script
# Run this after deploying new code to reload the application

# Touch restart.txt to trigger Passenger to restart the app
touch tmp/restart.txt

echo "Passenger app restart triggered"
