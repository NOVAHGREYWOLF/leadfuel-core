"""webchat-10: the one brand file stays readable. Contrast is recomputed from the file, not quoted."""
import json
import os

_P = os.path.join(os.path.dirname(__file__), os.pardir, "brand", "novahos-brand.json")


def _load():
    with open(_P, encoding="utf-8") as f:
        return json.load(f)


def _lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_text_and_accent_button_are_readable_in_both_themes():
    for theme, t in _load()["app"].items():
        for bg in ("ground", "surface", "surface-2"):
            assert ratio(t["ink"], t[bg]) >= 4.5, (theme, bg)
            assert ratio(t["ink-2"], t[bg]) >= 4.5, (theme, bg)
        assert ratio(t["on-accent"], t["accent"]) >= 4.5, theme
        assert ratio(t["accent"], t["ground"]) >= 3.0, theme


def test_every_colour_is_a_hex_and_greywolf_gold_is_not_invented():
    d = _load()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k != "gold":
                    yield from walk(v)
        elif isinstance(x, list):
            for v in x:
                yield from walk(v)
        elif isinstance(x, str) and x.startswith("#"):
            yield x
    cols = list(walk({k: v for k, v in d.items() if k in ("app", "mark", "greywolf")}))
    assert cols and all(len(c) == 7 and int(c[1:], 16) >= 0 for c in cols)
    assert d["greywolf"]["gold"] is None


def test_the_contrast_check_can_fail():
    assert ratio("#777777", "#808080") < 4.5
