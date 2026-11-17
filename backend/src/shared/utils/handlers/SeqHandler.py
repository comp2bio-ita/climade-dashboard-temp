
from dataclasses import dataclass
from typing import Iterable, Iterator


@dataclass
class FastaRecord:
    """
    Represents a single FASTA record.

    Example:
        >NC_000001.1 Homo sapiens chromosome 1
        ACTGACTG...
    """
    id: str
    description: str
    sequence: str


def parse_fasta(handle) -> Iterator[FastaRecord]:
    """
    Parse FASTA records from an open file-like object.

    Yields:
        FastaRecord objects one at a time.

    Example:
        with open("sequences.fasta") as handle:
            for record in parse_fasta(handle):
                print(record.id)
                print(record.sequence)
    """
    record_id = None
    description = ""
    sequence_parts = []

    for line in handle:
        line = line.strip()

        # Ignore blank lines
        if not line:
            continue

        if line.startswith(">"):
            # Emit the previous record
            if record_id is not None:
                yield FastaRecord(
                    id=record_id,
                    description=description,
                    sequence="".join(sequence_parts),
                )

            header = line[1:].strip()

            # FASTA ID is the first whitespace-delimited field
            parts = header.split(maxsplit=1)
            record_id = parts[0] if parts else ""
            description = parts[1] if len(parts) > 1 else ""
            sequence_parts = []

        else:
            # Remove whitespace from sequence lines
            sequence_parts.append(line.replace(" ", ""))

    # Emit the final record
    if record_id is not None:
        yield FastaRecord(
            id=record_id,
            description=description,
            sequence="".join(sequence_parts),
        )


def read_fasta(filename: str) -> list[FastaRecord]:
    """
    Read all FASTA records from a file.

    Returns:
        A list of FastaRecord objects.
    """
    with open(filename, "r") as handle:
        return list(parse_fasta(handle))


def write_fasta(
    records: Iterable[FastaRecord],
    filename: str,
    line_width: int = 150,
) -> None:
    """
    Write FASTA records to a file.

    Args:
        records:
            Iterable of FastaRecord objects.

        filename:
            Output FASTA filename.

        line_width:
            Number of sequence characters per line.
    """
    with open(filename, "w") as handle:
        for record in records:
            write_fasta_record(handle, record, line_width=line_width)


def write_fasta_record(
    handle,
    record: FastaRecord,
    line_width: int = 150,
) -> None:
    """
    Write one FastaRecord to an already-open file.
    """
    header = record.id

    if record.description:
        header += f" {record.description}"

    handle.write(f">{header}\n")

    sequence = record.sequence.replace(" ", "").replace("\n", "")

    for i in range(0, len(sequence), line_width):
        handle.write(sequence[i:i + line_width] + "\n")


def fasta_to_dict(filename: str) -> dict[str, FastaRecord]:
    """
    Read a FASTA file into a dictionary keyed by record ID.
    """
    return {
        record.id: record
        for record in read_fasta(filename)
    }
