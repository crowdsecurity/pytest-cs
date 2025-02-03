from pytest_cs.lib.text import nocolor


def test_simple() -> None:
    want = "Hello, world!"
    assert nocolor("Hello, world!") == want


def test_ansi() -> None:
    txt = "\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m \x1b[33mYellow\x1b[0m"
    want = "Red Green Yellow"
    assert nocolor(txt) == want
    txt = "b38f3abf63d9d3f0bd49fffb9f3c4280\x1b(B\x1b[m"
    want = "b38f3abf63d9d3f0bd49fffb9f3c4280"
    assert nocolor(txt) == want
