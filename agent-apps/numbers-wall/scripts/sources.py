"""Where a metric's next reading comes from. A metric names one of these functions in "source": {"from": "<name>", ...}.

Each function takes that source object and returns {"date": "YYYY-MM-DD", "value": <number>} for today's reading.
A key is read from the environment, where csc key set puts it for the session; it is never written to the inputs, the
page, or the output. Add a function here for any other service, report, or spreadsheet.
"""

import csv
import json
import os
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path


class MissingKey(Exception):
    def __init__(self, name):
        super().__init__(name)
        self.name = name


class SourceError(Exception):
    pass


def _key(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise MissingKey(name)
    return value


def _number(text, where):
    try:
        value = float(str(text).replace(",", "").strip())
        return int(value) if value.is_integer() else value
    except ValueError as error:
        raise SourceError(f"{where} holds {text!r}, which is not a number.") from error


def csv_last_row(source):
    """The last row of a CSV file: {"from": "csv_last_row", "path": "sales.csv", "date": "Date", "value": "Revenue"}."""
    path = Path(source.get("path", ""))
    if not path.is_file():
        raise SourceError(f"there is no file at {path}.")
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SourceError(f"{path} has no rows.")
    row = rows[-1]
    column = source.get("value", "value")
    if column not in row:
        raise SourceError(f"{path} has no column named {column!r}.")
    day = row.get(source.get("date", "date")) or date.today().isoformat()
    return {"date": day[:10], "value": _number(row[column], f"the column {column!r}")}


def plausible_visitors(source):
    """Today's visitors from Plausible: {"from": "plausible_visitors", "site": "example.com"}. Key: PLAUSIBLE_API_KEY."""
    key = _key("PLAUSIBLE_API_KEY")
    query = urllib.parse.urlencode({"site_id": source.get("site", ""), "period": "day", "metrics": "visitors"})
    request = urllib.request.Request(
        f"https://plausible.io/api/v1/stats/aggregate?{query}", headers={"Authorization": f"Bearer {key}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.load(response)
    except OSError as error:
        raise SourceError(f"Plausible did not answer ({error}).") from error
    value = body.get("results", {}).get("visitors", {}).get("value")
    if value is None:
        raise SourceError("Plausible's answer had no visitors count.")
    return {"date": date.today().isoformat(), "value": _number(value, "the visitors count")}
