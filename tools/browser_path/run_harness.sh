#!/bin/sh
# usage: run_harness.sh <corpus dir> <port> <framing>; retries the intermittent MediaPipe start-up failure until every video has a file
export NODE_PATH="$(dirname "$0")/../e2e/tools/node_modules" CORPUS_DIR="$1" FRAMES_PORT="$2"
total=$(python -I -c "import json,sys;print(len(json.load(open(sys.argv[1]+'/samples.json'))['samples']))" "$1")
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  have=$(ls "$1/browser/$3" 2>/dev/null | wc -l)
  [ "$have" -ge "$total" ] && break
  node "$(dirname "$0")/browser_harness.js" "$3" >> "$1/h_$3.log" 2>&1
  sleep 5
done
