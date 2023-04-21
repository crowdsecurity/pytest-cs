import json
import re
import subprocess

# match ANSI and ISO 2022 sequences
_control_sequences = re.compile(r'(\x1B[@-Z\\-_]|\x1B\([B\)]|\x1b\[.*?[mGKH])')


def strip_color(s):
    return _control_sequences.sub('', s)


def get_bouncers(**kw):
    """
    lookup bouncers by key=value
    """
    out = subprocess.check_output(
            ['cscli', 'bouncers', 'list', '-o', 'json'],
            encoding='utf-8')
    for bouncer in json.loads(out):
        for key, value in kw.items():
            if bouncer[key] == value:
                yield bouncer
