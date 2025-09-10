#!/bin/bash

APP_PATH="/home/davit/ownStuff/HeadCoin/blockchain.py"

# Keep track of process IDs (PIDs)
PIDS=()

cleanup() {
    echo "Stopping all Flask servers..."
    for PID in "${PIDS[@]}"; do
        kill "$PID" 2>/dev/null
    done
    exit 0
}

# Trap Ctrl+C (SIGINT) and call cleanup
trap cleanup SIGINT

for item in "5000:Davit" "5001:Kirill" "5002:Mathew"
do
    PORT="${item%%:*}"
    USERNAME="${item##*:}"

    echo "Starting Flask app on port $PORT for user $USERNAME"
    python3 "$APP_PATH" --port="$PORT" --user="$USERNAME" &
    PIDS+=($!)   # save PID of the background process
done

# Wait for all processes
wait
