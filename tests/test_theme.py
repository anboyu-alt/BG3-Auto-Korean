# tests/test_theme.py
def test_app_stylesheet_is_string():
    from bg3gui.theme import app_stylesheet
    css = app_stylesheet()
    assert isinstance(css, str)
    assert len(css) > 100

def test_color_constants_are_hex():
    import bg3gui.theme as theme
    for name in ["BG_APP", "BG_SIDEBAR", "GOLD", "GOLD_LIGHT", "TEXT_PRIMARY"]:
        val = getattr(theme, name)
        assert val.startswith("#"), f"{name} should be hex color, got {val}"
