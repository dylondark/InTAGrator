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

def tag_file(filepath):
    print(f"\nTagging: {filepath}")
    print("=" * 50)

    # 1. AcoustID fingerprint
    match = get_acoustid_match(filepath)
    if not match:
        print("No AcoustID match found.")
        return

    print(f"AcoustID match (score: {match['score']:.0%})")
    metadata = {**match}

    # 2. MusicBrainz
    if match["recording_id"]:
        mb = get_musicbrainz_metadata(match["recording_id"])
        metadata.update(mb)
        print(f"MusicBrainz data fetched")

    # 3. Last.fm track info
    if match["artist"] and match["title"]:
        lfm = get_lastfm_metadata(match["artist"], match["title"])
        metadata.update(lfm)
        artist_info = get_lastfm_artist_info(match["artist"])
        metadata.update(artist_info)
        print(f"Last.fm data fetched")

    # --- Print all collected metadata ---
    print("\n Full Metadata:")
    for key, value in metadata.items():
        if value:
            print(f"  {key:25s}: {value}")

    return metadata

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python songInfo.py <filename>")
        sys.exit(1) # Exit if no filename is provided
    
    filename = sys.argv[1]
    tag_file(filename)