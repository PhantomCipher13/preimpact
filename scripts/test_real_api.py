import urllib.request
import json
import time

t0 = time.time()
try:
    req = urllib.request.urlopen('http://127.0.0.1:8000/api/real')
    data = json.loads(req.read().decode())
    t1 = time.time()
    print(f"Status: {req.status} in {t1-t0:.3f}s")
    print(f"Mode: {data.get('mode')}")
    print(f"Bridges detected: {data.get('bridges_detected')}")
    print(f"Hospitals: {len(data.get('hospitals', []))}")
    print(f"Cyclone: {data.get('cyclone_scenario', {}).get('name')}")
    results = data.get("counterfactual_results", [])
    print(f"Results: {len(results)}")
    if results:
        print(f"Top result: {results[0].get('asset_id')} - {results[0].get('asset_name')}")
except Exception as e:
    print("Error:", e)
