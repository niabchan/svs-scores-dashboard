import ast
from pathlib import Path
from string import Formatter


APP_PATH = Path(__file__).with_name("app.py")
SUPPORTED_LOCALES = {"en", "es", "fr", "vi", "id"}


def _load_literal_assignment(name):
    """Read a top-level literal assignment without importing the Streamlit app."""
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"), filename=str(APP_PATH))

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)

    raise AssertionError(f"Could not find top-level assignment for {name!r} in app.py")


def _format_fields(value):
    fields = set()
    for _, field_name, _, _ in Formatter().parse(value):
        if field_name:
            fields.add(field_name)
    return fields


def test_language_selector_uses_expected_unique_locale_codes():
    languages = _load_literal_assignment("LANGUAGES")

    assert set(languages.values()) == SUPPORTED_LOCALES
    assert len(languages.values()) == len(set(languages.values()))


def test_translation_dictionary_matches_supported_locales():
    text = _load_literal_assignment("TEXT")

    assert set(text) == SUPPORTED_LOCALES


def test_every_locale_has_exactly_the_english_key_set():
    text = _load_literal_assignment("TEXT")
    canonical_keys = set(text["en"])

    assert canonical_keys, "The canonical English translation dictionary is empty."

    for locale, translations in text.items():
        missing = canonical_keys - set(translations)
        extra = set(translations) - canonical_keys
        assert not missing, f"{locale} is missing translation keys: {sorted(missing)}"
        assert not extra, f"{locale} has extra translation keys: {sorted(extra)}"


def test_translation_values_are_non_empty_strings():
    text = _load_literal_assignment("TEXT")

    for locale, translations in text.items():
        for key, value in translations.items():
            assert isinstance(value, str), f"{locale}.{key} must be a string"
            assert value.strip(), f"{locale}.{key} must not be blank"


def test_named_format_fields_match_english():
    text = _load_literal_assignment("TEXT")

    for key, english_value in text["en"].items():
        canonical_fields = _format_fields(english_value)
        for locale, translations in text.items():
            locale_fields = _format_fields(translations[key])
            assert locale_fields == canonical_fields, (
                f"{locale}.{key} format fields {sorted(locale_fields)} do not match "
                f"English fields {sorted(canonical_fields)}"
            )


def test_score_balance_caption_uses_chart_names_not_screen_positions():
    text = _load_literal_assignment("TEXT")
    directional_phrases = {
        "en": ("left chart", "right chart"),
        "es": ("gráfico de la izquierda", "gráfico de la derecha"),
        "fr": ("graphique de gauche", "graphique de droite"),
        "vi": ("biểu đồ bên trái", "biểu đồ bên phải"),
        "id": ("grafik sebelah kiri", "grafik sebelah kanan"),
    }

    for locale, translations in text.items():
        caption = translations["score_balance_caption"]
        before_label = translations["before_exclusion"].replace("**", "")
        after_label = translations["after_exclusion"].replace("**", "")

        assert before_label in caption, f"{locale} caption must name the Before Exclusion chart"
        assert after_label in caption, f"{locale} caption must name the After Exclusion chart"

        lowered_caption = caption.lower()
        for phrase in directional_phrases[locale]:
            assert phrase not in lowered_caption, (
                f"{locale}.score_balance_caption must not rely on screen position: {phrase!r}"
            )


def test_literal_t_calls_reference_known_translation_keys():
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"), filename=str(APP_PATH))
    text = _load_literal_assignment("TEXT")
    known_keys = set(text["en"])

    literal_t_keys = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "t"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }

    missing = literal_t_keys - known_keys
    assert not missing, (
        "Literal t() calls reference missing translation keys: "
        f"{sorted(missing)}"
    )
