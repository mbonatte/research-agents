import json

from pathlib import Path
from datetime import datetime

from app.usage import serialize_usage


def save_local_run_log(result):
    Path(".runs").mkdir(exist_ok=True)

    filename = datetime.now().strftime(".runs/run-%Y%m%d-%H%M%S.json")

    data = {
        "timestamp": datetime.now().isoformat(),
        "final_output": result.final_output,
        "last_agent": getattr(result.last_agent, "name", None),
        "new_items": [str(item) for item in result.new_items],
        "usage": serialize_usage(result),
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filename