import json
import unittest
from pathlib import Path

from offline_viewer import PAGE, parse_packet


PROJECT_DIR = Path(__file__).resolve().parents[1]


class ParsePacketTests(unittest.TestCase):
    def test_parses_a_valid_datacast_packet(self):
        channel, timestamp, samples = parse_packet(b"{'SHZ', 1507760140.530, 614, -916, 1095}")
        self.assertEqual(channel, "SHZ")
        self.assertEqual(timestamp, 1507760140.530)
        self.assertEqual(samples, [614, -916, 1095])

    def test_rejects_an_invalid_packet(self):
        with self.assertRaises(ValueError):
            parse_packet(b"not a datacast packet")

    def test_dashboard_includes_spectrogram_controls(self):
        self.assertIn('id="spectrogram-toggle"', PAGE)
        self.assertIn('id="spectrogram-channel"', PAGE)
        self.assertIn("function fftMagnitudes", PAGE)


class DatacastConfigTests(unittest.TestCase):
    def test_udp_port_is_written_as_a_string(self):
        config = json.loads((PROJECT_DIR / "config" / "UDP-data-streams.conf").read_text())
        self.assertEqual(config["OFFLINE-DEMO-MAC"]["Port"], "8888")

        setup_script = (PROJECT_DIR / "scripts" / "configure_shake_for_demo.sh").read_text()
        self.assertIn('"Port": "$PORT"', setup_script)


if __name__ == "__main__":
    unittest.main()
