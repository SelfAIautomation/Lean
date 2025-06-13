import json
import unittest
from unittest.mock import patch, MagicMock
import sys

# Ensure Algorithm.Python is on the path
sys.path.insert(0, 'Algorithm.Python')
import BinanceMinuteData as module


class BinanceMinuteDataTest(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_fetch_latest_kline(self, mock_urlopen):
        sample = [[1, '100', '110', '90', '105', '15', 2]]
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(sample).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        data = module.fetch_latest_kline('BTCUSDT')
        self.assertEqual(data['open'], 100.0)
        self.assertEqual(data['close'], 105.0)
        self.assertEqual(data['volume'], 15.0)


if __name__ == '__main__':
    unittest.main()
