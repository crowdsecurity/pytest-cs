from pytest_cs.lib import nocolor


def test_decode_simple():
    input_str = b'Hello, world!'
    expected_output_str = 'Hello, world!'
    decoded_str = nocolor.UTF8NoColorCodec().decode(input_str)[0]
    assert decoded_str == expected_output_str
    decoded_str = input_str.decode('utf8_nocolor')
    assert decoded_str == expected_output_str


def test_decode_ansi():
    input_str = b'\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m \x1b[33mYellow\x1b[0m'
    expected_output_str = 'Red Green Yellow'
    decoded_str = nocolor.UTF8NoColorCodec().decode(input_str)[0]
    assert decoded_str == expected_output_str
    decoded_str = input_str.decode('utf8_nocolor')
    assert decoded_str == expected_output_str
