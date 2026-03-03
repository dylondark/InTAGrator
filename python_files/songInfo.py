import sys

import acoustid
import requests
import musicbrainzngs
import re
import os
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv()
ACOUSTID_API_KEY = os.getenv("ACOUSTID_API_KEY")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
MUSICBRAINZ_APP = "InTAGrator/1.0"

musicbrainzngs.set_useragent(*MUSICBRAINZ_APP.split("/"))

def get_acoustid_match(filepath):
    """Step 1: Fingerprint the file and get recording_id, title, artist."""
    results = acoustid.match(ACOUSTID_API_KEY, filepath)
    for score, recording_id, title, artist in results:
        if score > 0.5:
            return {"score": score, "recording_id": recording_id, "title": title, "artist": artist}
    return None

def get_musicbrainz_metadata(recording_id):
    """Step 2: Use MusicBrainz recording_id to get album, release date, track number, label, tags, genres."""
    try:
        result = musicbrainzngs.get_recording_by_id(
            recording_id,
            includes=["artists", "releases", "tags", "genres"]
        )
        rec = result["recording"]
        metadata = {
            "mb_title": rec.get("title"),
            "mb_length_ms": rec.get("length"),
            "mb_tags": [t["name"] for t in rec.get("tag-list", [])],
            "mb_genres": [g["name"] for g in rec.get("genre-list", [])],
        }

        # Get album/release info from first release
        releases = rec.get("release-list", [])
        if releases:
            release = releases[0]
            metadata["album"] = release.get("title")
            metadata["release_date"] = release.get("date")
            metadata["track_number"] = release.get("medium-list", [{}])[0] \
                .get("track-list", [{}])[0].get("number")
            metadata["label"] = release.get("label-info-list", [{}])[0] \
                .get("label", {}).get("name")

        return metadata
    except Exception as e:
        print(f"MusicBrainz error: {e}")
        return {}

def get_lastfm_metadata(artist, title):
    """Step 3: Last.fm for tags, listeners, playcount, summary."""
    try:
        url = "http://ws.audioscrobbler.com/2.0/"
        params = {
            "method": "track.getInfo",
            "api_key": LASTFM_API_KEY,
            "artist": artist,
            "track": title,
            "format": "json"
        }
        r = requests.get(url, params=params).json()
        track = r.get("track", {})
        return {
            "lastfm_listeners": track.get("listeners"),
            "lastfm_playcount": track.get("playcount"),
            "lastfm_tags": [t["name"] for t in track.get("toptags", {}).get("tag", [])],
            "lastfm_summary": track.get("wiki", {}).get("summary", "").split("<a href")[0].strip(),
            "duration_ms": track.get("duration"),
        }
    except Exception as e:
        print(f"Last.fm error: {e}")
        return {}

def get_lastfm_artist_info(artist):
    """Step 4: Last.fm artist bio, country, similar artists."""
    try:
        url = "http://ws.audioscrobbler.com/2.0/"
        params = {
            "method": "artist.getInfo",
            "api_key": LASTFM_API_KEY,
            "artist": artist,
            "format": "json"
        }
        r = requests.get(url, params=params).json()
        a = r.get("artist", {})
        return {
            "artist_bio": a.get("bio", {}).get("summary", "").split("<a href")[0].strip(),
            "artist_listeners": a.get("stats", {}).get("listeners"),
            "artist_tags": [t["name"] for t in a.get("tags", {}).get("tag", [])],
            "similar_artists": [s["name"] for s in a.get("similar", {}).get("artist", [])],
        }
    except Exception as e:
        print(f"Last.fm artist error: {e}")
        return {}

def tag_file(filepath, verbose=False, use_musicbrainz=True, use_lastfm=True):
    if verbose:
        print(f"\nTagging: {filepath}")
        print("=" * 50)

    # 1. AcoustID fingerprint
    match = get_acoustid_match(filepath)
    if not match:
        if verbose:
            print("No AcoustID match found.")
        return

    if verbose:
        print(f"AcoustID match (score: {match['score']:.0%})")
    metadata = {**match}

    # 2. MusicBrainz
    if use_musicbrainz and match["recording_id"]:
        mb = get_musicbrainz_metadata(match["recording_id"])
        metadata.update(mb)
        if verbose:
            print(f"MusicBrainz data fetched")
    elif not use_musicbrainz and verbose:
        print("MusicBrainz skipped")

    # 3. Last.fm track info
    if use_lastfm and match["artist"] and match["title"]:
        lfm = get_lastfm_metadata(match["artist"], match["title"])
        metadata.update(lfm)
        artist_info = get_lastfm_artist_info(match["artist"])
        metadata.update(artist_info)
        if verbose:
            print(f"Last.fm data fetched")
    elif not use_lastfm and verbose:
        print("Last.fm skipped")

    if verbose:
        # --- Print all collected metadata ---
        print("\n Full Metadata:")
        for key, value in metadata.items():
            if value:
                print(f"  {key:25s}: {value}")
    else:
        # --- Write metadata to JSON file ---
        import json
        base = os.path.splitext(os.path.basename(filepath))[0]
        out_path = f"{base}_metadata.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(out_path)

    return metadata

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch metadata for a song file.")
    parser.add_argument("filename", help="Path to the audio file")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print all metadata to the console instead of writing a JSON file"
    )

    source_group = parser.add_argument_group("sources")
    source_group.add_argument(
        "--no-musicbrainz",
        action="store_true",
        help="Disable MusicBrainz lookups"
    )
    source_group.add_argument(
        "--no-lastfm",
        action="store_true",
        help="Disable Last.fm lookups"
    )

    args = parser.parse_args()
    tag_file(
        args.filename,
        verbose=args.verbose,
        use_musicbrainz=not args.no_musicbrainz,
        use_lastfm=not args.no_lastfm,
    )
