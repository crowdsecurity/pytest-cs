import json
import subprocess


def get_bouncers(**kw: dict[str, str]):
    """Lookup bouncers by key=value."""
    out = subprocess.check_output(["cscli", "bouncers", "list", "-o", "json"], encoding="utf8")
    for bouncer in json.loads(out):
        for key, value in kw.items():
            if bouncer[key] == value:
                yield bouncer
