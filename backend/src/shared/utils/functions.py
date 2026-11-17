from datetime import datetime, timedelta
from typing import Literal


def chunk_array(array: list[any], chunk_size=100):
    return [array[i:i + chunk_size] for i in range(0, len(array), chunk_size)]

def convert_str_time_to_datetime(str_date: str) -> datetime:

    if not str_date or str_date.strip().lower() == "null":
        return None

    str_formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",    # ISO 8601 with Zulu time
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S.%f",     # Date with microseconds
        "%Y-%m-%d %H:%M:%S",        # Date with time
        "%Y-%m-%d",                 # Date only
        "%Y-%m",                    # Year and month
        "%Y"                        # Year only
    ]


    for fmt in str_formats:
        try:
            dt = datetime.strptime(str_date, fmt)
            return dt
        except ValueError:
            continue

    return None

def convert_datetime_to_str_time(
    dt: datetime,
    dt_format: Literal[
        "%Y-%m-%dT%H:%M:%S.%fZ",    # ISO 8601 with Zulu time
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S.%f",     # Date with microseconds
        "%Y-%m-%d %H:%M:%S",        # Date with time
        "%Y-%m-%d",                 # Date only
        "%Y-%m",                    # Year and month
        "%Y"                        # Year only
    ] = "%Y-%m-%dT%H:%M:%SZ"
) -> str:

    if not dt:
        return None

    new_date_str = dt.strftime(dt_format)

    if dt_format == "%Y-%m-%dT%H:%M:%S.%fZ":
        new_date_str = new_date_str[:-3] + "Z"

    return new_date_str

def datetime_add(
    dt: datetime, 
    days: int = 0, 
    hours: int = 0, 
    minutes: int = 0, 
    seconds: int = 0
) -> datetime:
    if not dt or not isinstance(dt, datetime):
        return None
    
    dt = dt + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    return dt