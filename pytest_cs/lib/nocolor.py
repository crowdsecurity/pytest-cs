import codecs
import re

"""
A codec that strips ANSI control codes from its input.

Used for basic testing, not guaranteed to work outside of the
specific use case of this project.
"""


class UTF8NoColorCodec(codecs.Codec):
    CONTROL_CODE_REGEX = re.compile(
        # rb'(\x1B[@-Z\\-_]|\x1B\([B\)]|\x1b\[.*?[mGKH])'
        rb'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'
    )

    def decode(self, input, errors='strict'):
        return (self.CONTROL_CODE_REGEX.sub(b'', input).decode('utf8'), len(input))

    def encode(self, input, errors='strict'):
        return (input.encode('utf8'), len(input))


def lookup(encoding):
    if encoding == 'utf8_nocolor':
        return codecs.CodecInfo(
            name='utf8_nocolor',
            encode=codecs.utf_8_encode,
            decode=UTF8NoColorCodec().decode,
        )
    return None


codecs.register(lookup)
