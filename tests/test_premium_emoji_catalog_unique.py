from services.premium_emoji_service import DEFAULTS, catalog


def test_catalog_contains_valid_glyph_models():
    models = catalog()
    assert models
    assert all(isinstance(key, str) and key for key in models)
    assert all(isinstance(glyph, str) and glyph.strip() for glyph in models.values())
    for key, glyph in DEFAULTS.items():
        assert models[key] == glyph
