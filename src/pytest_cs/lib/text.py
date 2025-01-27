import re

csi_regex = re.compile(r'\x1B\[\d+(;\d+){0,2}m|\x1b\(B\x1B\[m')


def nocolor(s):
    return csi_regex.sub('', s,)
