"""Unit tests for ph_disaster_monitor."""

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from ph_disaster_monitor import (
    BoundingBox,
    Alert,
    deduplicate,
    format_text,
    format_json,
    _mag_label,
    _mentions_philippines,
    _classify_gdacs,
    _classify_reliefweb,
    load_state,
    save_state,
)


class TestBoundingBox(unittest.TestCase):
    """Test BoundingBox.contains()."""

    def setUp(self):
        self.box = BoundingBox(6.0, 9.0, 124.5, 127.5)

    def test_inside(self):
        self.assertTrue(self.box.contains(7.5, 126.0))

    def test_outside_north(self):
        self.assertFalse(self.box.contains(10.0, 126.0))

    def test_outside_south(self):
        self.assertFalse(self.box.contains(5.0, 126.0))

    def test_outside_east(self):
        self.assertFalse(self.box.contains(7.5, 128.0))

    def test_outside_west(self):
        self.assertFalse(self.box.contains(7.5, 124.0))

    def test_on_boundary(self):
        self.assertTrue(self.box.contains(6.0, 124.5))
        self.assertTrue(self.box.contains(9.0, 127.5))


class TestMagLabel(unittest.TestCase):
    """Test _mag_label()."""

    def test_major(self):
        self.assertEqual(_mag_label(7.8), "🔴 MAJOR")

    def test_strong(self):
        self.assertEqual(_mag_label(6.5), "🟠 STRONG")

    def test_moderate(self):
        self.assertEqual(_mag_label(5.5), "🟡 MODERATE")

    def test_light(self):
        self.assertEqual(_mag_label(4.2), "🔵 LIGHT")

    def test_minor(self):
        self.assertEqual(_mag_label(2.0), "⚪ MINOR")


class TestMentionsPhilippines(unittest.TestCase):
    """Test _mentions_philippines()."""

    def test_direct(self):
        self.assertTrue(_mentions_philippines("50 km N of Manila, Philippines"))

    def test_region(self):
        self.assertTrue(_mentions_philippines("Mindanao, Philippines"))

    def test_no_match(self):
        self.assertFalse(_mentions_philippines("50 km N of Tokyo, Japan"))


class TestClassifyGdacs(unittest.TestCase):
    """Test _classify_gdacs()."""

    def test_typhoon(self):
        self.assertEqual(_classify_gdacs("Red typhoon alert"), "typhoon")

    def test_cyclone(self):
        self.assertEqual(_classify_gdacs("Orange cyclone alert"), "typhoon")

    def test_flood(self):
        self.assertEqual(_classify_gdacs("Green flood alert"), "flood")

    def test_volcano(self):
        self.assertEqual(_classify_gdacs("Orange volcanic eruption"), "volcano")

    def test_earthquake(self):
        self.assertEqual(_classify_gdacs("Green earthquake alert"), "earthquake")

    def test_tsunami(self):
        self.assertEqual(_classify_gdacs("Red tsunami warning"), "tsunami")

    def test_drought(self):
        self.assertEqual(_classify_gdacs("Orange drought alert"), "drought")

    def test_skip_other(self):
        self.assertIsNone(_classify_gdacs("Unknown event type"))


class TestClassifyReliefweb(unittest.TestCase):
    """Test _classify_reliefweb()."""

    def test_typhoon(self):
        self.assertEqual(
            _classify_reliefweb("Typhoon MAYMAK makes landfall in Luzon"),
            "typhoon",
        )

    def test_flood(self):
        self.assertEqual(_classify_reliefweb("Heavy flooding in Cagayan"), "flood")

    def test_landslide(self):
        self.assertEqual(_classify_reliefweb("Landslide in Davao"), "landslide")

    def test_fire(self):
        self.assertEqual(_classify_reliefweb("Factory fire in Manila"), "fire")

    def test_unknown(self):
        self.assertEqual(
            _classify_reliefweb("Political unrest reported"), "disaster"
        )


class TestDeduplicate(unittest.TestCase):
    """Test deduplicate()."""

    def _make_alert(self, source, title, mag=None, atype="earthquake"):
        return Alert(
            source=source, alert_type=atype, severity="🟡 MODERATE",
            title=title, detail="test", event_id=f"{source}-{title[:10]}",
            magnitude=mag,
        )

    def test_title_dedup(self):
        a1 = self._make_alert("usgs", "M5.7 Earthquake — Sarangani", 5.7)
        a2 = self._make_alert("gdacs", "M5.7 Earthquake — Sarangani", 5.7)
        result = deduplicate([a1, a2])
        self.assertEqual(len(result), 1)

    def test_usgs_authoritative_for_earthquake(self):
        usgs = self._make_alert("usgs", "M5.7 Earthquake — Sarangani", 5.7)
        gdacs = self._make_alert(
            "gdacs",
            "Green earthquake (Magnitude 5.7M, Depth:35km) in Philippines",
            5.7,
        )
        result = deduplicate([usgs, gdacs])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].source, "usgs")

    def test_keeps_different_magnitudes(self):
        usgs = self._make_alert("usgs", "M5.7 Earthquake — Sarangani", 5.7)
        gdacs = self._make_alert(
            "gdacs",
            "Green earthquake (Magnitude 4.2M, Depth:10km) in Philippines",
            4.2,
        )
        result = deduplicate([usgs, gdacs])
        self.assertEqual(len(result), 2)

    def test_non_earthquake_never_suppressed(self):
        a1 = self._make_alert("gdacs", "Red typhoon alert", atype="typhoon")
        a2 = self._make_alert("reliefweb", "Typhoon MAYMAK update", atype="typhoon")
        result = deduplicate([a1, a2])
        self.assertEqual(len(result), 2)

    def test_sort_by_magnitude_desc(self):
        a1 = self._make_alert("usgs", "M4.0 Earthquake — A", 4.0)
        a2 = self._make_alert("usgs", "M6.5 Earthquake — B", 6.5)
        a3 = self._make_alert("usgs", "M5.0 Earthquake — C", 5.0)
        result = deduplicate([a1, a2, a3])
        mags = [a.magnitude for a in result]
        self.assertEqual(mags, [6.5, 5.0, 4.0])


class TestFormatText(unittest.TestCase):
    """Test format_text()."""

    def test_output_contains_emoji(self):
        alert = Alert(
            source="usgs", alert_type="earthquake", severity="🟡 MODERATE",
            title="M5.7 Earthquake — Test",
            detail="Depth: 35 km | test", event_id="test-1",
            magnitude=5.7,
        )
        output = format_text([alert])
        self.assertIn("🌋", output)
        self.assertIn("M5.7 Earthquake", output)
        self.assertIn("Stay alert", output)


class TestFormatJson(unittest.TestCase):
    """Test format_json()."""

    def test_valid_json(self):
        alert = Alert(
            source="usgs", alert_type="earthquake", severity="🟡 MODERATE",
            title="M5.7 Earthquake — Test",
            detail="Depth: 35 km", event_id="test-1",
            magnitude=5.7,
        )
        output = format_json([alert])
        parsed = json.loads(output)
        self.assertEqual(parsed["count"], 1)
        self.assertEqual(parsed["alerts"][0]["source"], "usgs")
        self.assertIn("generated_at", parsed)


class TestAlertEmoji(unittest.TestCase):
    """Test Alert.emoji()."""

    def test_earthquake_emoji(self):
        a = Alert("usgs", "earthquake", "🟠", "title", "detail", "id")
        self.assertEqual(a.emoji(), "🌋")

    def test_typhoon_emoji(self):
        a = Alert("gdacs", "typhoon", "🔴", "title", "detail", "id")
        self.assertEqual(a.emoji(), "🌀")

    def test_unknown_emoji(self):
        a = Alert("test", "unknown", "🔵", "title", "detail", "id")
        self.assertEqual(a.emoji(), "⚠️")


class TestStatePersistence(unittest.TestCase):
    """Test load_state() / save_state()."""

    def test_roundtrip(self):
        import tempfile
        from pathlib import Path
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        try:
            ids = {"usgs-123", "gdacs-456", "reliefweb-789"}
            save_state(path, ids)
            loaded = load_state(path)
            self.assertEqual(loaded, ids)
        finally:
            path.unlink(missing_ok=True)

    def test_missing_file_returns_empty(self):
        from pathlib import Path
        result = load_state(Path("/nonexistent/path/state.json"))
        self.assertEqual(result, set())


if __name__ == "__main__":
    unittest.main()
