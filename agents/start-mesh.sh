#!/bin/bash
# Aegis mesh startup script — starts bobiverse hub, bob agent, aegis-runtime agent
# Usage: ./start-mesh.sh [start|stop|status]

NAME=bobiverse
HUB_DIR=/home/ubuntu/Manifold/federation
LOG_DIR=/tmp

start() {
    echo "Starting $NAME mesh agents..."
    
    # Kill existing
    pkill -f "register-bob.mjs" 2>/dev/null
    pkill -f "register-aegis-runtime.mjs" 2>/dev/null
    sleep 1
    
    # Start bob + aegis-runtime hub (updated register-bob.mjs handles both)
    cd "$HUB_DIR"
    nohup node register-bob.mjs > "$LOG_DIR/bob.log" 2>&1 &
    echo "bob started (PID $!)"
    
    sleep 2
    
    # Verify
    curl -s http://localhost:8777/agents | python3 -c "
import json, sys
d = json.load(sys.stdin)
agents = [a['name'] for a in d.get('agents', []) if a.get('hub') == 'bobiverse']
print('bobiverse agents:', agents)
" 2>/dev/null || echo "Warning: hub not responding"
}

stop() {
    echo "Stopping $NAME mesh agents..."
    pkill -f "register-bob.mjs" 2>/dev/null
    pkill -f "register-aegis-runtime.mjs" 2>/dev/null
    echo "stopped"
}

status() {
    curl -s http://localhost:8777/agents | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('Hub:', d.get('hub', 'unknown'))
print('Peers:', d.get('peers', 0))
print('Agents:', d.get('agents', 0))
agents = [a['name'] for a in d.get('agents', []) if a.get('hub') == 'bobiverse']
print('bobiverse agents:', agents)
" 2>/dev/null || echo "Hub not responding"
}

case "${1:-start}" in
    start) start ;;
    stop) stop ;;
    status) status ;;
    *) echo "Usage: $0 {start|stop|status}" ;;
esac
