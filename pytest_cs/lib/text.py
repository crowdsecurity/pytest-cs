import re


def nocolor(s):
    return re.sub(
        # r'(\x1B[@-Z\\-_]|\x1B\([B\)]|\x1b\[.*?[mGKH])'
        r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])',
        '',
        s
    )
