#!/usr/bin/env python3
"""Lay out one of the kit's demo trips the way its person hands it over.

USAGE:
    python3 make_trip.py DEST --trip lisbon|italy [--no-coordinates] [--media FOLDER]

DEST is a workspace. It receives pulled/items.json, the posts the person handed over in the shape gather.py reads
from its first door (ts, caption, media, place, geo) with the person's handle, and pulled/media/ copied from the
photographs and clips in media/ beside this file (public domain, sources in media/SOURCES.md), or in --media.

  lisbon  mara.makes with @ines.draws, mon 14 to fri 18 sep 2026: alfama, graça (a clip of the tram), belém, sintra,
          bairro alto; each caption says what they did there, in the person's own voice.
  italy   jonas.byrail, tue 2 to fri 5 jun 2026: the train into Bolzano, a rowing boat on Lago di Braies, the long
          drive south to the road across Campo Imperatore, and the same afternoon the view down to Lago di Campotosto.

Every caption is written from its photograph (what the frame shows), so no word on screen contradicts the picture
under it: the empty lane they had to themselves, the tram they rode up the hill, the tower at the end of the walk
along the river, the palace's yellow walls they got lost in, the fountain they stayed out for; the empty compartment
and its table, the boat's bow on green water under the peaks, the straight road they drove all morning for, the blue
ridges and the lake below.

--no-coordinates leaves lat and lon off every post, the trip a person shares from a phone with location off: the
films are made without the map.
"""
import argparse
import calendar
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

LISBON = [
    {"file": "media/IMG_0412.jpg", "seed": "alfama.jpg", "taken": "2026-09-14T09:12:00", "caption": "alfama at seven, the lane to ourselves @ines.draws",
     "place": "Alfama, Lisbon", "lat": 38.7110, "lon": -9.1300},
    {"file": "media/IMG_0431.mp4", "seed": "clip-tram.mp4", "taken": "2026-09-15T17:40:00", "caption": "tram up to graça, standing room only",
     "place": "Graça, Lisbon", "lat": 38.7168, "lon": -9.1306},
    {"file": "media/IMG_0455.jpg", "seed": "belem.jpg", "taken": "2026-09-16T11:05:00", "caption": "walked the river all the way out to belém",
     "place": "Belém, Lisbon", "lat": 38.6976, "lon": -9.2063},
    {"file": "media/IMG_0478.jpg", "seed": "sintra.jpg", "taken": "2026-09-17T14:20:00", "caption": "train to sintra, lost in the yellow palace @ines.draws",
     "place": "Sintra", "lat": 38.7977, "lon": -9.3874},
    {"file": "media/IMG_0502.jpg", "seed": "bairro-alto.jpg", "taken": "2026-09-18T20:15:00", "caption": "last night, the fountain lit up, we stayed @ines.draws",
     "place": "Bairro Alto, Lisbon", "lat": 38.7134, "lon": -9.1448},
]
ITALY = [
    {"file": "media/DSC_2207.jpg", "seed": "train.jpg", "taken": "2026-06-02T16:10:00",
     "caption": "Window seat on the old regional train, the table to myself", "place": "Bolzano", "lat": 46.4967, "lon": 11.3579},
    {"file": "media/DSC_2241.jpg", "seed": "dolomites.jpg", "taken": "2026-06-03T10:30:00",
     "caption": "Rowing out on the green water, the peaks straight ahead", "place": "Lago di Braies", "lat": 46.6946, "lon": 12.0853},
    {"file": "media/DSC_2288.jpg", "seed": "road-trip.jpg", "taken": "2026-06-05T09:40:00",
     "caption": "Drove south all morning for this, the road dead straight across the plain", "place": "Campo Imperatore",
     "lat": 42.4300, "lon": 13.6200},
    {"file": "media/DSC_2301.jpg", "seed": "mountain-hike.jpg", "taken": "2026-06-05T15:20:00",
     "caption": "From the top, blue ridges all the way out and the lake far below", "place": "Lago di Campotosto",
     "lat": 42.5000, "lon": 13.4000},
]
TRIPS = {
    "lisbon": {"handle": "mara.makes", "posts": LISBON},
    "italy": {"handle": "jonas.byrail", "posts": ITALY},
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest", type=Path)
    ap.add_argument("--trip", choices=list(TRIPS), required=True)
    ap.add_argument("--media", type=Path, default=Path(__file__).resolve().parent / "media",
                    help="the folder holding the photographs and clips (default: media/ beside this file)")
    ap.add_argument("--no-coordinates", action="store_true")
    a = ap.parse_args()
    pulled = a.dest / "pulled"
    (pulled / "media").mkdir(parents=True, exist_ok=True)
    rows = []
    trip = TRIPS[a.trip]
    for p in trip["posts"]:
        src = a.media / p["seed"]
        if not src.exists():
            sys.exit(f"{src} is missing")
        shutil.copyfile(src, pulled / p["file"])
        row = {"ts": calendar.timegm(datetime.fromisoformat(p["taken"]).timetuple()), "caption": p["caption"],
               "media": [p["file"]], "place": p["place"]}
        if not a.no_coordinates:
            row["geo"] = [p["lat"], p["lon"]]
        rows.append(row)
    items = {"source": "the posts the person handed over", "handle": trip["handle"], "posts": rows}
    (pulled / "items.json").write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} posts{' without coordinates' if a.no_coordinates else ''} to {pulled}/items.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
