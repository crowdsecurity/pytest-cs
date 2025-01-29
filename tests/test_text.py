from pytest_cs.lib.text import nocolor


def test_simple() -> None:
    input = "Hello, world!"
    expected_output = "Hello, world!"
    assert nocolor(input) == expected_output


def test_ansi() -> None:
    input = "\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m \x1b[33mYellow\x1b[0m"
    expected_output = "Red Green Yellow"
    assert nocolor(input) == expected_output
    input = "b38f3abf63d9d3f0bd49fffb9f3c4280\x1b(B\x1b[m"
    expected_output = "b38f3abf63d9d3f0bd49fffb9f3c4280"
    assert nocolor(input) == expected_output
