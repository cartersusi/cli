#!/bin/bash

KB_TO_GB=$((1 << 20))

if [ -z "$1" ]; then
  echo "Usage: $0 <application_name>"
  exit 1
fi

APP_NAME="$1"

TOTAL_PROCESSES=$(pgrep -fi "$APP_NAME" | wc -l)

if [ "$TOTAL_PROCESSES" -eq 0 ]; then
  echo "No processes found for application: $APP_NAME"
  exit 1
fi

TOTAL_MEMORY_KB=$(ps aux | grep -i "$APP_NAME" | grep -v grep | awk '{sum+=$6} END {print sum}')
TOTAL_MEMORY_GB=$(echo "scale=2; $TOTAL_MEMORY_KB / $KB_TO_GB" | bc)

echo "Total processes: $TOTAL_PROCESSES"
echo "Total memory usage: $TOTAL_MEMORY_GB GB"