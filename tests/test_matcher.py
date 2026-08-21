from __future__ import annotations

import unittest

from nummailai.matcher import AreaMatcher, haversine_distance, normalize_text
from nummailai.models import (
    BranchesConfig,
    KeywordsConfig,
    LocationConfig,
    MatchingConfig,
    OutageEvent,
)


class TestMatcher(unittest.TestCase):

    def setUp(self):
        self.sample_event = OutageEvent(
            event_id="test1234",
            start_date_raw="20 ส.ค. 2569 13:30",
            finish_date_raw="21 ส.ค. 2569 00:15",
            start_datetime=None,
            finish_datetime=None,
            latitude=13.8240,
            longitude=100.4478,
            impact_branch="มหาสวัสดิ์",
            branch_code="56",
            reason="ท่อแตกรั่ว",
            impact_area="ถนนประชาอุทิศ ซอยคอกวัว น้ำไม่ไหล",
            area_name="ถนนประชาอุทิศ จุดงาน",
            pipe_size="200",
            pipe_type="PVC",
            work_person="ช่างธีรชัย",
            active=True,
            impact_branch_str="56",
        )

    def test_haversine_distance(self):
        # Distance between identical points is 0
        dist = haversine_distance(13.7563, 100.5018, 13.7563, 100.5018)
        self.assertAlmostEqual(dist, 0.0, places=3)

        # Distance between Grand Palace (13.7500, 100.4914) and Victory Monument (13.7649, 100.5383) is approx ~5.3 km
        dist2 = haversine_distance(13.7500, 100.4914, 13.7649, 100.5383)
        self.assertTrue(4.5 < dist2 < 6.0)

    def test_normalize_text(self):
        raw = " ถนนประชาอุทิศ \u200b ซอย 1 "
        clean = normalize_text(raw)
        self.assertEqual(clean, "ถนนประชาอุทิศ ซอย 1")

    def test_hybrid_match_radius(self):
        # User is very close to event (13.8240, 100.4478)
        cfg = MatchingConfig(
            mode="hybrid",
            location=LocationConfig(enabled=True, latitude=13.8250, longitude=100.4480, radius_km=2.0),
            keywords=KeywordsConfig(enabled=False, terms=[]),
            branches=BranchesConfig(enabled=False, names=[]),
        )
        matcher = AreaMatcher(cfg)
        result = matcher.match(self.sample_event)
        self.assertTrue(result.matched)
        self.assertTrue(result.matched_radius)
        self.assertIsNotNone(result.distance_km)
        self.assertTrue(result.distance_km < 1.0)

    def test_hybrid_match_keyword(self):
        # User is far away, but keyword matches "ประชาอุทิศ"
        cfg = MatchingConfig(
            mode="hybrid",
            location=LocationConfig(enabled=True, latitude=13.5000, longitude=100.1000, radius_km=1.0),
            keywords=KeywordsConfig(enabled=True, terms=["ประชาอุทิศ", "ลาดพร้าว"]),
            branches=BranchesConfig(enabled=False, names=[]),
        )
        matcher = AreaMatcher(cfg)
        result = matcher.match(self.sample_event)
        self.assertTrue(result.matched)
        self.assertFalse(result.matched_radius)
        self.assertIn("ประชาอุทิศ", result.matched_keywords)

    def test_hybrid_match_branch(self):
        # Match by branch name
        cfg = MatchingConfig(
            mode="hybrid",
            location=LocationConfig(enabled=False),
            keywords=KeywordsConfig(enabled=False),
            branches=BranchesConfig(enabled=True, names=["มหาสวัสดิ์"]),
        )
        matcher = AreaMatcher(cfg)
        result = matcher.match(self.sample_event)
        self.assertTrue(result.matched)
        self.assertTrue(result.matched_branch)

    def test_no_match(self):
        cfg = MatchingConfig(
            mode="hybrid",
            location=LocationConfig(enabled=True, latitude=13.5000, longitude=100.1000, radius_km=1.0),
            keywords=KeywordsConfig(enabled=True, terms=["รามคำแหง", "สุขุมวิท 71"]),
            branches=BranchesConfig(enabled=True, names=["บางเขน"]),
        )
        matcher = AreaMatcher(cfg)
        result = matcher.match(self.sample_event)
        self.assertFalse(result.matched)


if __name__ == "__main__":
    unittest.main()
