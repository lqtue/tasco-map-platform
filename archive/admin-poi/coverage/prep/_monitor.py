"""Poll the GEE building-export tasks until none are PENDING/RUNNING."""
import time
from collections import Counter

import ee

ee.Initialize(project="propane-avatar-430409-r2")
DEADLINE = time.time() + 5 * 3600  # safety cap: 5h

while True:
    states = Counter()
    for t in ee.data.listOperations():
        md = t.get("metadata", {})
        if md.get("description", "").startswith("ob_"):
            states[md.get("state", "?")] += 1
    active = states.get("PENDING", 0) + states.get("RUNNING", 0)
    print(time.strftime("%H:%M:%S"), dict(states), flush=True)
    if active == 0 or time.time() > DEADLINE:
        print("DONE" if active == 0 else "TIMEOUT", flush=True)
        break
    time.sleep(120)
