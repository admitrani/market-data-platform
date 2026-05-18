"""Command-line interface for market data ingestion and warehouse loading."""

from __future__ import annotations

import argparse
import logging
from datetime import date

from ingestion.clients.binance_spot import BinanceSpotClient
from ingestion.pipeline import BackfillRequest, IncrementalRequest, IngestionPipeline
from ingestion.state.watermark import GCSWatermarkStore
from ingestion.storage.gcs_raw import GCSRawWriter
from warehouse.load_gcs_to_bq import RawKlinesLoadConfig, load_raw_klines_from_gcs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Market data platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backfill = subparsers.add_parser("backfill", help="Backfill raw klines into GCS")
    backfill.add_argument("--bucket", required=True, help="Target raw GCS bucket name")
    backfill.add_argument("--symbol", required=True, help="Trading pair symbol, e.g. BTCUSDT")
    backfill.add_argument("--interval", required=True, help="Binance interval, Phase 1 CORE: 1h")
    backfill.add_argument("--start-date", required=True, help="Inclusive start date: YYYY-MM-DD")
    backfill.add_argument("--end-date", required=True, help="Inclusive end date: YYYY-MM-DD")

    incremental = subparsers.add_parser(
        "incremental",
        help="Run bounded incremental raw ingestion using a GCS watermark",
    )
    incremental.add_argument("--bucket", required=True, help="Target raw GCS bucket name")
    incremental.add_argument("--symbol", required=True, help="Trading pair symbol, e.g. BTCUSDT")
    incremental.add_argument("--interval", required=True, help="Binance interval, Phase 1 CORE: 1h")
    incremental.add_argument(
        "--bootstrap-start-date",
        required=True,
        help="Start date used only when no watermark exists: YYYY-MM-DD",
    )
    incremental.add_argument(
        "--end-date",
        required=True,
        help="Inclusive end date. Required to prevent accidental large-cost runs.",
    )

    load_bq_raw = subparsers.add_parser(
        "load-bq-raw",
        help="Load raw GCS Parquet files into BigQuery raw table",
    )
    load_bq_raw.add_argument("--project-id", required=True)
    load_bq_raw.add_argument("--dataset-id", default="raw")
    load_bq_raw.add_argument("--table-id", default="raw_klines")
    load_bq_raw.add_argument("--gcs-uri", required=True)

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

    elif args.command == "incremental":
        request = IncrementalRequest(
            source="binance_spot",
            dataset="klines",
            symbol=args.symbol,
            interval=args.interval,
            bootstrap_start_date=date.fromisoformat(args.bootstrap_start_date),
            end_date=date.fromisoformat(args.end_date),
        )

        pipeline = IngestionPipeline(
            client=BinanceSpotClient(),
            writer=GCSRawWriter(bucket_name=args.bucket),
            watermark_store=GCSWatermarkStore(bucket_name=args.bucket),
        )

        result = pipeline.run_incremental(request)

        logging.info(
            "Incremental completed: start_date_used=%s partitions_written=%s rows_written=%s",
            result.start_date_used.isoformat(),
            result.partitions_written,
            result.rows_written,
        )

        if result.watermark_before:
            logging.info(
                "Watermark before: last_open_time_ms=%s",
                result.watermark_before.last_open_time_ms,
            )
        else:
            logging.info("Watermark before: none")

        if result.watermark_after:
            logging.info(
                "Watermark after: last_open_time_ms=%s",
                result.watermark_after.last_open_time_ms,
            )
        else:
            logging.info("Watermark after: none")

        for output in result.outputs:
            logging.info("Wrote %s rows to %s", output.row_count, output.gcs_uri)

    elif args.command == "load-bq-raw":
        config = RawKlinesLoadConfig(
            project_id=args.project_id,
            dataset_id=args.dataset_id,
            table_id=args.table_id,
            gcs_uri=args.gcs_uri,
        )

        destination = load_raw_klines_from_gcs(config=config)

        logging.info("Loaded raw klines into BigQuery table %s", destination)


if __name__ == "__main__":
    main()
