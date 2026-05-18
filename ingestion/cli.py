"""Command-line interface for market data ingestion."""

from __future__ import annotations

import argparse
import logging
from datetime import date

from ingestion.clients.binance_spot import BinanceSpotClient
from ingestion.pipeline import BackfillRequest, IngestionPipeline
from ingestion.storage.gcs_raw import GCSRawWriter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Market data ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backfill = subparsers.add_parser("backfill", help="Backfill raw klines into GCS")
    backfill.add_argument("--bucket", required=True, help="Target raw GCS bucket name")
    backfill.add_argument("--symbol", required=True, help="Trading pair symbol, e.g. BTCUSDT")
    backfill.add_argument("--interval", required=True, help="Binance interval, Phase 1 CORE: 1h")
    backfill.add_argument("--start-date", required=True, help="Inclusive start date: YYYY-MM-DD")
    backfill.add_argument("--end-date", required=True, help="Inclusive end date: YYYY-MM-DD")

    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    args = parse_args()

    if args.command == "backfill":
        request = BackfillRequest(
            source="binance_spot",
            dataset="klines",
            symbol=args.symbol,
            interval=args.interval,
            start_date=date.fromisoformat(args.start_date),
            end_date=date.fromisoformat(args.end_date),
        )

        pipeline = IngestionPipeline(
            client=BinanceSpotClient(),
            writer=GCSRawWriter(bucket_name=args.bucket),
        )

        result = pipeline.run_backfill(request)

        logging.info(
            "Backfill completed: partitions_written=%s rows_written=%s",
            result.partitions_written,
            result.rows_written,
        )

        for output in result.outputs:
            logging.info("Wrote %s rows to %s", output.row_count, output.gcs_uri)


if __name__ == "__main__":
    main()
