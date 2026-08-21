from __future__ import annotations

import unittest
from datetime import datetime

from nummailai.parser import (
    generate_event_id,
    parse_float,
    parse_raw_event,
    parse_thai_datetime,
)


class TestThaiParser(unittest.TestCase):

    def test_parse_thai_datetime_valid(self):
        dt = parse_thai_datetime("20 ส.ค. 2569 13:30")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 8)
        self.assertEqual(dt.day, 20)
        self.assertEqual(dt.hour, 13)
        self.assertEqual(dt.minute, 30)

    def test_parse_thai_datetime_different_months(self):
        dt_jan = parse_thai_datetime("01 ม.ค. 2569 00:00")
        self.assertEqual(dt_jan.month, 1)
        self.assertEqual(dt_jan.year, 2026)

        dt_dec = parse_thai_datetime("31 ธ.ค. 2568 23:59")
        self.assertEqual(dt_dec.month, 12)
        self.assertEqual(dt_dec.year, 2025)

    def test_parse_thai_datetime_invalid(self):
        self.assertIsNone(parse_thai_datetime(""))
        self.assertIsNone(parse_thai_datetime(None))
        self.assertIsNone(parse_thai_datetime("invalid date format"))

    def test_parse_float(self):
        self.assertEqual(parse_float("13.824096"), 13.824096)
        self.assertEqual(parse_float(100.447783), 100.447783)
        self.assertIsNone(parse_float(None))
        self.assertIsNone(parse_float(""))
        self.assertIsNone(parse_float("null"))
        self.assertIsNone(parse_float("invalid"))

    def test_generate_event_id(self):
        raw1 = {
            "startdate": "20 ส.ค. 2569 13:30",
            "finishdate": "21 ส.ค. 2569 00:15",
            "impactbranch": "มหาสวัสดิ์",
            "latitude": "13.859218",
            "longtitude": "100.385062",
            "areaname": "ถนนประชาอุทิศ",
            "reason": "ท่อแตกรั่ว",
        }
        raw2 = dict(raw1)
        id1 = generate_event_id(raw1)
        id2 = generate_event_id(raw2)
        self.assertEqual(id1, id2)
        self.assertEqual(len(id1), 16)

        raw3 = dict(raw1, areaname="ถนนอื่น")
        id3 = generate_event_id(raw3)
        self.assertNotEqual(id1, id3)

    def test_parse_raw_event(self):
        raw = {
            "startdate": "20 ส.ค. 2569 13:30",
            "finishdate": "21 ส.ค. 2569 00:15",
            "latitude": "13.859218",
            "longtitude": "100.385062",
            "impactbranch": "มหาสวัสดิ์",
            "branchcode": "56",
            "reason": "ท่อแตกรั่ว",
            "impactarea": "ถนนประชาอุทิศ น้ำไม่ไหล",
            "areaname": "ถนนประชาอุทิศ จุดงาน",
            "pipesize": "200",
            "pipetype": "PVC",
            "workperson": "ช่างธีรชัย",
            "active": "1",
            "impactbranchstr": "56",
        }
        event = parse_raw_event(raw)
        self.assertEqual(event.impact_branch, "มหาสวัสดิ์")
        self.assertEqual(event.branch_code, "56")
        self.assertEqual(event.latitude, 13.859218)
        self.assertEqual(event.longitude, 100.385062)
        self.assertTrue(event.active)
        self.assertTrue(event.is_urgent)
        self.assertTrue(event.has_coordinates)
        self.assertIn("13.859218,100.385062", event.google_maps_url)


if __name__ == "__main__":
    unittest.main()
