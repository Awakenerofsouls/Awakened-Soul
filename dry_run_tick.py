import sys, time
sys.path.insert(0, str('.'))

import heartbeat
heartbeat.running = True
heartbeat.tick_count = 0
heartbeat.session_start = time.time()

print('=== DRY RUN TICK ===')
try:
    heartbeat.do_internal_tick()
    print('do_internal_tick: ok')
except Exception as e:
    print(f'do_internal_tick ERROR: {e}')

try:
    heartbeat._psych_tick()
    print('_psych_tick: ok')
except Exception as e:
    print(f'_psych_tick ERROR: {e}')

print('=== CHECK OUTPUT ===')
import psychological_state
ps = psychological_state.get_state()
output = ps.get_state()
lines = output.split('\n')
for line in lines:
    if 'ThirdEye' in line or 'third_eye' in line.lower():
        print(line)

print('=== STATE FILE WRITTEN? ===')
from pathlib import Path
ps_file = Path('.') / 'psychological_state.md'
if ps_file.exists():
    print(f'psychological_state.md written — {ps_file.stat().st_size} bytes')
    content = ps_file.read_text()
    print(content[-300:])
else:
    print('No psychological_state.md written')