import argparse
import logging
import sys

from dotenv import load_dotenv

from models.env_models import EnvSettings
from services.DatabaseService import DatabaseService
from services.normalization.service import (
    curate_location_normalized,
    get_curation_row,
    normalize_location,
    normalize_pending_locations,
    strategy_available,
    LOCATION_NORMALIZED_MAX_LENGTH,
)


def _build_database_service() -> DatabaseService:
    settings = EnvSettings()
    return DatabaseService(
        host=settings.DASH_HOST,
        port=settings.DASH_PORT,
        database=settings.DASH_DATABASE,
        user=settings.DASH_USER,
        password=settings.DASH_PASSWORD,
    )


def _format_curation_value(value: str | None) -> str:
    return value if value is not None else "(null)"


def _validate_curation_value(value: str) -> str | None:
    if not value.strip():
        return "location_normalized must not be empty"
    if len(value) > LOCATION_NORMALIZED_MAX_LENGTH:
        return (
            f"location_normalized exceeds {LOCATION_NORMALIZED_MAX_LENGTH} characters"
        )
    return None


def _cmd_curate(args: argparse.Namespace) -> int:
    validation_error = _validate_curation_value(args.value)
    if validation_error:
        print(validation_error, file=sys.stderr)
        return 1

    database_service = _build_database_service()
    row = get_curation_row(database_service, args.accession_id)
    if row is None:
        print(f"Row not found: {args.accession_id}", file=sys.stderr)
        return 1

    current = row["location_normalized"]
    new_value = args.value

    print(f"accession_id: {row['accession_id']}")
    print(f"location:     {row['location']}")
    print(f"current:      {_format_curation_value(current)}")
    print(f"new:          {new_value}")
    print()

    current_display = _format_curation_value(current)
    prompt = (
        f'You are changing location_normalized from {current_display} to "{new_value}". '
        "Confirm? [y/N]: "
    )

    if not args.yes:
        answer = input(prompt).strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return 0

    curate_location_normalized(database_service, args.accession_id, new_value)
    print("Updated.")
    return 0


def _cmd_pending(args: argparse.Namespace) -> int:
    if not strategy_available(args.country):
        print(
            f"Location normalization service not available for country: {args.country}",
            file=sys.stderr,
        )
        return 1

    database_service = _build_database_service()
    summary = normalize_pending_locations(database_service, country=args.country)
    print(summary)
    return 0


def _cmd_location(args: argparse.Namespace) -> int:
    if not strategy_available(args.country):
        print(
            f"Location normalization service not available for country: {args.country}",
            file=sys.stderr,
        )
        return 1

    normalized = normalize_location(args.country, args.value)
    if normalized is None:
        print("Unresolved")
        return 2

    print(normalized)
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Geographic location normalization service",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    pending_parser = subparsers.add_parser(
        "pending",
        help="Normalize pending database locations for a country",
    )
    pending_parser.add_argument(
        "--country",
        required=True,
        help="Country name as stored before the colon (e.g. Brazil)",
    )
    pending_parser.set_defaults(handler=_cmd_pending)

    curate_parser = subparsers.add_parser(
        "curate",
        help="Manually set location_normalized on a single row",
    )
    curate_parser.add_argument(
        "--accession-id",
        required=True,
        help="Primary key of ncbi_sequence_data",
    )
    curate_parser.add_argument(
        "--value",
        required=True,
        help='Canonical location_normalized string (e.g. "Brazil: Minas Gerais, Belo Horizonte")',
    )
    curate_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation",
    )
    curate_parser.set_defaults(handler=_cmd_curate)

    location_parser = subparsers.add_parser(
        "location",
        help="Normalize a single location without modifying the database",
    )
    location_parser.add_argument(
        "--country",
        required=True,
        help="Country name as stored before the colon (e.g. Brazil)",
    )
    location_parser.add_argument(
        "--value",
        required=True,
        help='Raw location string (e.g. "Brazil: Belo Horizonte, Minas Gerais")',
    )
    location_parser.set_defaults(handler=_cmd_location)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
