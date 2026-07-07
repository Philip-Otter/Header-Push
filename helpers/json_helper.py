import json

def clone_json(data: dict) -> dict: return json.loads(json.dumps(data))
