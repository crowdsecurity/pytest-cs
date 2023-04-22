from pytest_cs.lib.text import nocolor


def test_simple():
    input = 'Hello, world!'
    expected_output = 'Hello, world!'
    assert nocolor(input) == expected_output


def test_ansi():
    input = '\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m \x1b[33mYellow\x1b[0m'
    expected_output = 'Red Green Yellow'
    assert nocolor(input) == expected_output
