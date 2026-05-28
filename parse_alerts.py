import json

with open('alerts.json', encoding='utf-16') as f:
    alerts = json.load(f)

for a in alerts:
    instance = a.get('most_recent_instance', {})
    loc = instance.get('location', {})
    rule = a.get('rule', {})
    print(f"[{rule.get('description')}] {loc.get('path')}:{loc.get('start_line')}")
