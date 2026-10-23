from utils.text_normalization import normalize_filter_text


def test_normalizes_arabic_yeh_and_kaf_to_persian_forms():
    assert normalize_filter_text("يكي كلمه") == normalize_filter_text("یکی کلمه")


def test_removes_diacritics_tatweel_and_invisible_characters():
    assert normalize_filter_text("كِتابـ\u200cي") == "کتابی"


def test_collapses_whitespace_and_casefolds():
    assert normalize_filter_text("  TEST   WORD  ") == "test word"


def test_empty_text_normalizes_to_empty_string():
    assert normalize_filter_text("   ") == ""
