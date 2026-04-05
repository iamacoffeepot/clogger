from ragger.utils import snake_case


def test_basic():
    assert snake_case("Dragon Slayer I") == "dragon_slayer_i"


def test_possessive():
    assert snake_case("Cook's Assistant") == "cooks_assistant"


def test_curly_apostrophe():
    assert snake_case("Cook\u2019s Assistant") == "cooks_assistant"


def test_special_characters():
    assert snake_case("Black Knights' Fortress") == "black_knights_fortress"


def test_already_snake():
    assert snake_case("dragon_slayer_i") == "dragon_slayer_i"


def test_hyphens():
    assert snake_case("Dorgesh-Kaan") == "dorgesh_kaan"


def test_roman_numerals():
    assert snake_case("Monkey Madness II") == "monkey_madness_ii"
