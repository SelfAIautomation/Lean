import os
import sys
import unittest
from unittest.mock import patch

# Ensure project root is on the path so Toolbox modules can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Provide a minimal ccxt stub before importing the downloader
class _CcxtStub:
    exchanges = []

sys.modules.setdefault('ccxt', _CcxtStub())

# Insert a minimal google.cloud.bigquery stub so the module can be imported
import types
_bq_module = types.ModuleType('bigquery')
_bq_module.Client = object
_cloud_module = types.ModuleType('cloud')
_cloud_module.bigquery = _bq_module
_google_module = types.ModuleType('google')
_google_module.cloud = _cloud_module
sys.modules.setdefault('google', _google_module)
sys.modules.setdefault('google.cloud', _cloud_module)
sys.modules.setdefault('google.cloud.bigquery', _bq_module)

from ToolBox.CcxtDataDownloader import ccxt_gcp_downloader as downloader


class BigQueryClientStub:
    def __init__(self):
        self.rows = []

    def insert_rows_json(self, table_ref, rows):
        self.rows.append((table_ref, rows))
        return []


class CcxtGcpDownloaderTests(unittest.TestCase):
    def test_data_inserted_for_each_exchange(self):
        dataset = 'ds'
        table = 'tbl'
        os.environ['BQ_DATASET'] = dataset
        os.environ['BQ_TABLE'] = table

        stub_client = BigQueryClientStub()
        exchanges = ['binance', 'kraken']

        with patch('ToolBox.CcxtDataDownloader.ccxt_gcp_downloader.bigquery.Client', return_value=stub_client):
            with patch('ToolBox.CcxtDataDownloader.ccxt_gcp_downloader.ccxt.exchanges', exchanges):
                with patch('ToolBox.CcxtDataDownloader.ccxt_gcp_downloader.fetch_exchange_data', side_effect=lambda ex: [{'id': ex}]):
                    downloader.fetch_and_store_all_exchanges()

        self.assertEqual(len(stub_client.rows), len(exchanges))
        os.environ.pop('BQ_DATASET')
        os.environ.pop('BQ_TABLE')


if __name__ == '__main__':
    unittest.main()
