import unittest

from offline_viewer import PAGE, parse_packet


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


if __name__ == "__main__":
    unittest.main()
