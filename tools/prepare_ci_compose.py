"""Use the actual local stack with prebuilt images in an isolated CI project."""

import sys
from pathlib import Path
import yaml

config = yaml.safe_load(Path("compose.yaml").read_text(encoding="utf8"))
config.pop("name", None)
for name in ["backend", "ml"]:
    config["services"][name].pop("build")
    config["services"][name]["image"] = f"alfa-potok-{name}:{sys.argv[1]}"
backend = config["services"]["backend"]
backend["ports"] = ["127.0.0.1:18080:8000"]
backend["environment"]["LLM_BASE_URL"] = ""
backend["healthcheck"] = {
    "test": [
        "CMD",
        "python",
        "-c",
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/')",
    ],
    "interval": "3s",
    "timeout": "3s",
    "retries": 30,
}
Path(sys.argv[2]).write_text(
    yaml.safe_dump(config, sort_keys=False), encoding="utf8"
)
