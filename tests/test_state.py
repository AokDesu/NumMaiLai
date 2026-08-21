from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nummailai.models import MatchResult, OutageEvent
from nummailai.state import StateManager


class TestStateManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / "state.json"
        self.state_manager = StateManager(str(self.state_file))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_deduplication(self):
        event = OutageEvent(
            event_id="unique_id_999",
            start_date_raw="20 ส.ค. 2569 13:30",
            finish_date_raw="21 ส.ค. 2569 00:15",
            start_datetime=None,
            finish_datetime=None,
            latitude=13.8240,
            longitude=100.4478,
            impact_branch="มหาสวัสดิ์",
            branch_code="56",
            reason="ท่อแตกรั่ว",
            impact_area="ถนนประชาอุทิศ",
            area_name="จุดงาน",
            pipe_size="200",
            pipe_type="PVC",
            work_person="ช่าง",
            active=True,
            impact_branch_str="56",
        )
        match_result = MatchResult(matched=True, summary_reasons=["Test match"])

        # Initially not notified
        self.assertFalse(self.state_manager.is_already_notified("unique_id_999"))

        # Mark notified
        self.state_manager.mark_notified(event, match_result)
        self.assertTrue(self.state_manager.is_already_notified("unique_id_999"))

        # Reload from disk and verify persistence
        new_manager = StateManager(str(self.state_file))
        self.assertTrue(new_manager.is_already_notified("unique_id_999"))


if __name__ == "__main__":
    unittest.main()
