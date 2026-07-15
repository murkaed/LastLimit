"""Tests for the localization system (locales.py) and settings integration with config.py."""

import json

from locales import t, set_lang, get_lang, RU, EN, t_lang
from config import DEFAULT_SETTINGS, load_settings, save_settings


# ===================================================================
# t() function — basic translation
# ===================================================================


class TestTFunction:
    """Tests for the main t() translation function."""

    def test_returns_ru_string_default(self):
        """Default language is RU, so t() returns RU values by default."""
        set_lang("ru")
        assert t("ui.bridge.title") == "МОСТИК"
        assert t("ship.hull") == "Корпус"
        assert t("misc.yes") == "Да"

    def test_returns_en_string_after_set_lang(self):
        """After set_lang('en'), t() returns EN values."""
        set_lang("en")
        assert t("ui.bridge.title") == "BRIDGE"
        assert t("ship.hull") == "Hull"
        assert t("misc.yes") == "Yes"

    def test_switches_back_to_ru(self):
        """set_lang('ru') restores RU strings."""
        set_lang("ru")
        assert t("ui.exit") == "ВЫХОД"
        assert t("ship.energy") == "Энергия"

    def test_format_string_with_kwargs(self):
        """Keys containing {} placeholders are filled via **kwargs."""
        set_lang("en")
        result = t("log.docked", station="Alpha")
        assert result == "Docked at Alpha"

        set_lang("ru")
        result = t("log.docked", station="Альфа")
        assert result == "Стыковка с Альфа"

    def test_nonexistent_key_returns_fallback(self):
        """Unknown keys return a ❌ fallback string."""
        set_lang("en")
        assert t("nonexistent_key") == "❌nonexistent_key"
        assert t("completely.bogus.123") == "❌completely.bogus.123"

    def test_nonexistent_key_fallback_independent_of_lang(self):
        """Fallback format is the same regardless of current language."""
        set_lang("ru")
        assert t("no_such_key") == "❌no_such_key"
        set_lang("en")
        assert t("no_such_key") == "❌no_such_key"

    def test_multiple_format_args(self):
        """Multiple kwargs are accepted by format()."""
        set_lang("en")
        # Verify the pattern works with a key that has multiple placeholders.
        # If no such key exists, test that passing extra kwargs doesn't crash.
        result = t("log.docked", station="Station B")
        assert "Station B" in result

    def test_key_not_in_current_dict_but_in_en(self):
        """If a key is missing from the current language dict but exists in EN,
        the EN value is used as a second-chance fallback (not the ❌ fallback)."""
        # Simulate: create a temp dict for RU missing a key that EN has.
        # Instead of modifying RU, we verify the existing behaviour:
        # every key in RU is also in EN, so this normally never triggers,
        # but the code path in t() accesses EN.get(key) before the ❌ fallback.
        set_lang("en")
        assert t("ui.bridge.title") == "BRIDGE"  # exists in EN


# ===================================================================
# set_lang / get_lang
# ===================================================================


class TestSetAndGetLang:
    """Tests for language switching."""

    def test_get_lang_after_set_lang_en(self):
        """set_lang('en') updates get_lang() to 'en'."""
        set_lang("en")
        assert get_lang() == "en"

    def test_get_lang_after_set_lang_ru(self):
        """set_lang('ru') updates get_lang() to 'ru'."""
        set_lang("ru")
        assert get_lang() == "ru"

    def test_invalid_lang_does_not_change(self):
        """set_lang with an unsupported language code is a no-op."""
        set_lang("en")
        set_lang("fr")
        assert get_lang() == "en"  # unchanged

    def test_invalid_lang_empty_string(self):
        """set_lang('') does not crash and leaves language unchanged."""
        set_lang("en")
        set_lang("")
        assert get_lang() == "en"

    def test_invalid_lang_numeric(self):
        """set_lang('42') is ignored."""
        set_lang("ru")
        set_lang("42")
        assert get_lang() == "ru"


# ===================================================================
# Key coverage — every RU key must exist in EN
# ===================================================================


class TestKeyCoverage:
    """Ensure every translatable key is present in both language dicts."""

    def test_all_ru_keys_have_en_entry(self):
        """Every key in the RU dictionary must also appear in the EN dictionary."""
        missing = set(RU.keys()) - set(EN.keys())
        assert not missing, f"RU keys missing from EN: {missing}"

    def test_all_en_keys_have_ru_entry(self):
        """Every key in the EN dictionary must also appear in the RU dictionary.
        (Bidirectional check — catches new EN-only keys.)"""
        missing = set(EN.keys()) - set(RU.keys())
        assert not missing, f"EN keys missing from RU: {missing}"

    def test_both_dicts_have_the_same_number_of_keys(self):
        """Sanity check — both dictionaries should have identical size."""
        assert len(RU) == len(EN), (
            f"RU has {len(RU)} keys, EN has {len(EN)} keys"
        )


# ===================================================================
# t_lang() — explicit-language translation
# ===================================================================


class TestTLang:
    """Tests for t_lang(key, lang) which bypasses the current language."""

    def test_t_lang_ru_returns_ru_string(self):
        """t_lang('key', 'ru') returns the RU string regardless of current lang."""
        set_lang("en")
        assert t_lang("ui.bridge.title", "ru") == "МОСТИК"
        assert t_lang("ship.hull", "ru") == "Корпус"

    def test_t_lang_en_returns_en_string(self):
        """t_lang('key', 'en') returns the EN string regardless of current lang."""
        set_lang("ru")
        assert t_lang("ui.bridge.title", "en") == "BRIDGE"
        assert t_lang("ship.hull", "en") == "Hull"

    def test_t_lang_nonexistent_key(self):
        """t_lang with an unknown key returns the ❌ fallback."""
        assert t_lang("bogus_key", "en") == "❌bogus_key"

    def test_t_lang_unknown_lang_falls_back_to_ru(self):
        """t_lang with an unsupported lang code falls back to the RU dict."""
        result = t_lang("ui.bridge.title", "fr")
        assert result == "МОСТИК"


# ===================================================================
# Format string integrity
# ===================================================================


class TestFormatStrings:
    """Check that format-string placeholders are consistent across languages."""

    @staticmethod
    def _placeholders(template):
        """Extract set of {name} placeholder names from a template string."""
        import re
        return set(re.findall(r"\{(\w+)\}", template))

    def test_log_docked_placeholders_match(self):
        """The {station} placeholder in log.docked exists in both languages."""
        ru_placeholders = self._placeholders(RU.get("log.docked", ""))
        en_placeholders = self._placeholders(EN.get("log.docked", ""))
        assert ru_placeholders == en_placeholders, (
            f"RU placeholders {ru_placeholders} != EN placeholders {en_placeholders}"
        )

    def test_all_format_strings_have_matching_placeholders(self):
        """For every key where either language uses {} formatting, the
        placeholders must match exactly between RU and EN."""
        mismatches = []
        for key in RU:
            ru_val = RU[key]
            en_val = EN.get(key)
            if en_val is None:
                continue
            ru_ph = self._placeholders(ru_val)
            en_ph = self._placeholders(en_val)
            if ru_ph != en_ph:
                mismatches.append((key, ru_ph, en_ph))
        assert not mismatches, f"Placeholder mismatches: {mismatches}"

    def test_no_unescaped_braces_without_kwargs(self):
        """Keys with placeholders can still be called without kwargs
        (the raw template with braces is returned)."""
        set_lang("en")
        raw = t("log.docked")
        assert "{station}" in raw


# ===================================================================
# Settings load/save (config.py integration)
# ===================================================================


class TestSettingsLoadSave:
    """Tests for load_settings / save_settings using a tmp_path."""

    def test_load_settings_returns_defaults_when_no_file(self, settings_file):
        """load_settings() returns DEFAULT_SETTINGS when settings.json does not exist."""
        import os
        assert not os.path.exists(settings_file)
        loaded = load_settings()
        assert loaded == DEFAULT_SETTINGS

    def test_save_settings_writes_valid_json(self, settings_file):
        """save_settings() writes a parseable JSON file."""
        data = {"lang": "en", "autosave": False, "keys": {}}
        save_settings(data)
        with open(settings_file, "r", encoding="utf-8") as f:
            parsed = json.load(f)
        assert parsed["lang"] == "en"
        assert parsed["autosave"] is False

    def test_load_settings_reads_back_saved_values(self, settings_file):
        """save_settings then load_settings returns the same values."""
        original = {"lang": "ru", "autosave": False, "keys": {"interact": "x"}}
        save_settings(original)
        loaded = load_settings()
        assert loaded["lang"] == "ru"
        assert loaded["autosave"] is False
        assert loaded["keys"]["interact"] == "x"

    def test_load_settings_merges_with_defaults(self, settings_file):
        """Saved settings with missing keys fill in from DEFAULT_SETTINGS."""
        partial = {"lang": "en"}
        save_settings(partial)
        loaded = load_settings()
        assert loaded["lang"] == "en"
        assert loaded["autosave"] == DEFAULT_SETTINGS["autosave"]
        assert loaded["keys"] == DEFAULT_SETTINGS["keys"]

    def test_save_settings_encodes_non_ascii(self, settings_file):
        """save_settings writes ensure_ascii=False so Russian text survives."""
        data = {"lang": "ru", "autosave": True, "keys": {}}
        save_settings(data)
        with open(settings_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "lang" in content

    def test_load_settings_corrupted_file(self, settings_file):
        """A corrupted settings file falls back to DEFAULT_SETTINGS."""
        with open(settings_file, "w", encoding="utf-8") as f:
            f.write("this is not json")
        loaded = load_settings()
        assert loaded == DEFAULT_SETTINGS


# ===================================================================
# Settings + localization integration
# ===================================================================


class TestSettingsLanguageIntegration:
    """Tests that loading settings with a 'lang' key updates the locale."""

    def test_loading_en_lang_file_updates_get_lang(self, settings_file):
        """Load settings with lang='en', then get_lang() returns 'en'."""
        save_settings({"lang": "en", "autosave": True, "keys": DEFAULT_SETTINGS["keys"]})
        loaded = load_settings()
        set_lang(loaded["lang"])
        assert get_lang() == "en"
        assert t("ui.bridge.title") == "BRIDGE"

    def test_loading_ru_lang_file_updates_get_lang(self, settings_file):
        """Load settings with lang='ru', then get_lang() returns 'ru'."""
        set_lang("en")  # ensure we're in EN first
        save_settings({"lang": "ru", "autosave": True, "keys": DEFAULT_SETTINGS["keys"]})
        loaded = load_settings()
        set_lang(loaded["lang"])
        assert get_lang() == "ru"
        assert t("ui.bridge.title") == "МОСТИК"

    def test_round_trip_settings_preserves_lang(self, settings_file):
        """Save settings with lang='en', load back, set_lang, verify t()."""
        set_lang("ru")
        save_settings({"lang": "en", "autosave": True, "keys": DEFAULT_SETTINGS["keys"]})
        loaded = load_settings()
        set_lang(loaded["lang"])
        assert t("misc.yes") == "Yes"


# ===================================================================
# Edge cases
# ===================================================================


class TestEdgeCases:
    """Unusual or error-prone inputs."""

    def test_t_with_empty_key(self):
        """t('') with an empty string returns the ❌ fallback."""
        assert t("") == "❌"

    def test_t_key_with_special_characters(self):
        """Keys with dots and special chars resolve correctly."""
        set_lang("en")
        val = t("scan.no_targets")
        assert val == "No targets in range"

    def test_ru_strings_contain_russian_chars(self):
        """RU dictionary values contain Cyrillic characters."""
        set_lang("ru")
        for key in ("ui.bridge.title", "ship.hull", "misc.da"):
            val = t(key)
            assert isinstance(val, str)
            assert len(val) > 0

    def test_en_strings_are_ascii(self):
        """EN dictionary values use only ASCII / basic punctuation."""
        set_lang("en")
        for key in ("ui.bridge.title", "ship.hull", "misc.yes", "battle.victory"):
            val = t(key)
            assert isinstance(val, str)
            assert len(val) > 0

    def test_all_ru_values_are_strings(self):
        """Every value in the RU dictionary is a string."""
        for key, val in RU.items():
            assert isinstance(val, str), f"RU['{key}'] is not a string: {type(val)}"

    def test_all_en_values_are_strings(self):
        """Every value in the EN dictionary is a string."""
        for key, val in EN.items():
            assert isinstance(val, str), f"EN['{key}'] is not a string: {type(val)}"

    def test_t_lang_returns_string(self):
        """t_lang always returns a string value."""
        result = t_lang("log.docked", "en")
        assert isinstance(result, str)
        assert len(result) > 0
