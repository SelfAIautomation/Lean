"""CCXT data downloader with optional BigQuery storage.

This module fetches data from all supported CCXT exchanges. When the
``BQ_DATASET`` and ``BQ_TABLE`` environment variables are defined the
downloaded data will be inserted into the provided Google BigQuery
table using :class:`google.cloud.bigquery.Client`.

Environment variables
---------------------
BQ_DATASET : str
    Destination BigQuery dataset id.
BQ_TABLE : str
    Destination BigQuery table id within the dataset.
"""

import os
import ccxt
from google.cloud import bigquery


def fetch_exchange_data(exchange_id):
    """Fetch data for a single exchange. This is a small wrapper around
    ``ccxt``. The returned data must be serialisable as JSON.
    """
    exchange = getattr(ccxt, exchange_id)()
    return exchange.fetch_markets()


def store_to_bigquery(dataset_id, table_id, data):
    """Store ``data`` into the given BigQuery dataset/table.

    Parameters
    ----------
    dataset_id : str
        BigQuery dataset id.
    table_id : str
        BigQuery table id.
    data : Sequence[Mapping]
        Iterable of rows to insert.
    """
    client = bigquery.Client()
    table_ref = f"{dataset_id}.{table_id}"
    errors = client.insert_rows_json(table_ref, data)
    if errors:
        raise RuntimeError(f"Failed to insert rows: {errors}")


def fetch_and_store_all_exchanges():
    """Fetch data for all ccxt exchanges and optionally store it in BigQuery."""
    dataset = os.getenv("BQ_DATASET")
    table = os.getenv("BQ_TABLE")

    for exchange_id in ccxt.exchanges:
        data = fetch_exchange_data(exchange_id)
        if dataset and table:
            store_to_bigquery(dataset, table, data)

