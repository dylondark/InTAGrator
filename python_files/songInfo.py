import sys
import acoustid
import requests
import musicbrainzngs
import re
import os
import argparse
import json

from bs4 import BeautifulSoup
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv()
ACOUSTID_API_KEY = os.getenv("ACOUSTID_API_KEY")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
GENIUS_API_KEY = os.getenv("GENIUS_API_KEY")
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
    """Step 2: MusicBrainz recording — album, release date, track number, label, tags."""
    try:
        result = musicbrainzngs.get_recording_by_id(
            recording_id,
            includes=["artists", "releases", "tags"]
        )

        rec = result["recording"]
        metadata = {
            "mb_title":     rec.get("title"),
            "mb_length_ms": rec.get("length"),
            "mb_tags":      [t["name"] for t in rec.get("tag-list", [])],
        
            "mb_genres":       [g["name"] for g in rec.get("genre-list", [])],
            "mb_isrcs":        rec.get("isrc-list", []),          # e.g. ["USUM71703861"]
            "mb_rating":       rec.get("rating", {}).get("value"),
            "mb_disambiguation": rec.get("disambiguation"),       # e.g. "live version"
            "mb_aliases":      [a["alias"] for a in rec.get("alias-list", [])],
        
            "mb_artist_credit": " ".join([
                ac.get("name") or ac.get("artist", {}).get("name", "")
                for ac in rec.get("artist-credit", [])
                if isinstance(ac, dict)
            ]),
        
            "mb_isrc_list": rec.get("isrc-list", []),
        
            "mb_urls": [
                {"type": r.get("type"), "url": r.get("url", {}).get("resource")}
                for r in rec.get("url-relation-list", [])
            ],
        
            "mb_work_id": next((
                r.get("work", {}).get("id")
                for r in rec.get("work-relation-list", [])
                if r.get("type") == "performance"
            ), None),
        }

        releases = rec.get("release-list", [])
        
        if releases:
            release = releases[0]
            rg = release.get("release-group", {})
            medium = release.get("medium-list", [{}])[0]
            track  = medium.get("track-list", [{}])[0]

            metadata.update({
                "album":        release.get("title"),
                "release_date": release.get("date"),
                "track_number": track.get("number"),
                "label":        release.get("label-info-list", [{}])[0].get("label", {}).get("name"),
                "release_id":       release.get("id"),            
                "release_country":  release.get("country"),       
                "release_status":   release.get("status"),        
                "release_barcode":  release.get("barcode"),
                "total_tracks":     medium.get("track-count"),
                "disc_number":      medium.get("position"),
                "media_format":     medium.get("format"),         
                "catalog_number":   release.get("label-info-list", [{}])[0].get("catalog-number"),
                "release_group_id":   rg.get("id"),
                "release_group_type": rg.get("type"),             
                "release_group_secondary_types": [
                    t for t in rg.get("secondary-type-list", [])  
                ],
            })

        return metadata
    
    except Exception as e:
        print(f"MusicBrainz recording error: {e}")
        return {}

def get_musicbrainz_artist_detail(artist_name):
    """Step 3: MusicBrainz artist — country, career dates, members, type, URLs."""
    try:
        search = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        artists = search.get("artist-list", [])
        if not artists:
            return {}

        artist_id = artists[0]["id"]
        result = musicbrainzngs.get_artist_by_id(
            artist_id,
            includes=["tags", "artist-rels", "url-rels"]
        )
        a = result["artist"]

        members = []
        for rel in a.get("artist-relation-list", []):
            if rel.get("type") in ("member of band", "is member of band"):
                members.append(rel["artist"]["name"])

        urls = {}
        for rel in a.get("url-relation-list", []):
            rel_type = rel.get("type", "")
            url = rel.get("url", {}).get("resource", "")
            if rel_type and url:
                urls[rel_type] = url

        life = a.get("life-span", {})

        return {
            "artist_type":    a.get("type"),
            "artist_country": a.get("country"),
            "artist_area":    a.get("area", {}).get("name"),
            "career_begin":   life.get("begin"),
            "career_end":     life.get("end") if life.get("ended") else None,
            "band_members":   members if members else None,
            "mb_artist_tags": [t["name"] for t in a.get("tag-list", [])],
            "artist_urls":    urls if urls else None,
        }
    except Exception as e:
        print(f"MusicBrainz artist detail error: {e}")
        return {}

def get_lastfm_metadata(artist, title):
    """Step 4: Last.fm track — tags, listeners, playcount, summary."""
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
            "lastfm_tags":      [t["name"] for t in track.get("toptags", {}).get("tag", [])],
            "lastfm_summary":   track.get("wiki", {}).get("summary", "").split("<a href")[0].strip(),
            "duration_ms":      track.get("duration"),
        }
    except Exception as e:
        print(f"Last.fm error: {e}")
        return {}

def get_lastfm_artist_info(artist):
    """Step 5: Last.fm artist — bio, similar artists, listener stats."""
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
            "artist_bio":       a.get("bio", {}).get("summary", "").split("<a href")[0].strip(),
            "artist_listeners": a.get("stats", {}).get("listeners"),
            "artist_tags":      [t["name"] for t in a.get("tags", {}).get("tag", [])],
            "similar_artists":  [s["name"] for s in a.get("similar", {}).get("artist", [])],
        }
    except Exception as e:
        print(f"Last.fm artist error: {e}")
        return {}

def get_genius_data(artist, title):
    """Step 6: Genius — lyrics URL, description, featured artists, producers, writers, stats."""
    if not GENIUS_API_KEY:
        print("Genius API key not set, skipping.")
        return {}
    try:
        headers = {"Authorization": f"Bearer {GENIUS_API_KEY}"}

        r = requests.get(
            "https://api.genius.com/search",
            params={"q": f"{artist} {title}"},
            headers=headers
        ).json()

        hits = r.get("response", {}).get("hits", [])
        if not hits:
            r2 = requests.get(
                "https://api.genius.com/search",
                params={"q": title},
                headers=headers
            ).json()
            hits = r2.get("response", {}).get("hits", [])
        if not hits:
            return {}

        # Find best match — lenient word-level check
        song = None
        for hit in hits:
            result = hit.get("result", {})
            primary = result.get("primary_artist", {}).get("name", "").lower()
            artist_lower = artist.lower()
            if any(word in primary for word in artist_lower.split()) or \
               any(word in artist_lower for word in primary.split()):
                song = result
                break
        if not song:
            song = hits[0].get("result", {})

        # Fetch full song detail
        song_id = song.get("id")
        detail = requests.get(
            f"https://api.genius.com/songs/{song_id}",
            params={"text_format": "plain"},
            headers=headers
        ).json()
        s = detail.get("response", {}).get("song", {})

        featured = [a["name"] for a in s.get("featured_artists", [])]
        producers = [a["name"] for a in s.get("producer_artists", [])]
        writers   = [a["name"] for a in s.get("writer_artists", [])]

        description = s.get("description", {}).get("plain", "").strip()
        if description and len(description) > 300:
            description = description[:300].rsplit(" ", 1)[0] + "..."

        return {
            "genius_url":          song.get("url"),
            "genius_title":        song.get("full_title"),
            "genius_release_date": s.get("release_date_for_display"),
            "genius_description":  description if description else None,
            "featured_artists":    featured if featured else None,
            "producers":           producers if producers else None,
            "writers":             writers if writers else None,
            "annotation_count":    s.get("annotation_count"),
            "genius_pageviews":    s.get("stats", {}).get("pageviews"),
        }
    except Exception as e:
        print(f"Genius error: {e}")
        return {}
    
def get_genius_lyrics(genius_url):
    """Scrape lyrics from a Genius song page."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(genius_url, headers=headers, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})
        if not containers:
            return None

        lyrics_parts = []
        for container in containers:
            # Replace <br> tags with newlines before extracting text
            for br in container.find_all("br"):
                br.replace_with("\n")
            # Strip annotation links but keep their text
            for a in container.find_all("a"):
                a.unwrap()
            lyrics_parts.append(container.get_text())

        lyrics = "\n".join(lyrics_parts).strip()

        if lyrics:
            return {'lyrics': lyrics}
        else:
            return None

    except Exception as e:
        print(f"Lyrics scrape error: {e}")
        return None

def get_cover_art(release_id):
    """Fetch cover art from Cover Art Archive using MB release_id."""
    try:
        url = f"https://coverartarchive.org/release/{release_id}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        images = data.get("images", [])
        front = next((img for img in images if img.get("front")), images[0] if images else None)
        
        if not front:
            return {}
            
        return {
            "cover_art_url":       front.get("image"),          # full resolution
            "cover_art_thumb_250": front.get("thumbnails", {}).get("250"),
            "cover_art_thumb_500": front.get("thumbnails", {}).get("500"),
            "cover_art_approved":  front.get("approved"),
        }
    except Exception as e:
        print(f"Cover art error: {e}")
        return {}

def fetch_metadata(filepath):
    print(f"\nTagging: {filepath}")
    print("=" * 50)

    # 1. AcoustID fingerprint
    match = get_acoustid_match(filepath)
    if not match:
        print("No AcoustID match found.")
        return

    print(f"AcoustID match (score: {match['score']:.0%})")

    metadata = {**match}

    # 2. MusicBrainz recording
    if match["recording_id"]:
        mb = get_musicbrainz_metadata(match["recording_id"])
        metadata.update(mb)
        print("MusicBrainz recording data fetched")

    # 3. MusicBrainz artist detail
    if match["artist"]:
        mb_artist = get_musicbrainz_artist_detail(match["artist"])
        metadata.update(mb_artist)
        print("MusicBrainz artist detail fetched")

    # 4. Last.fm track
    if match["artist"] and match["title"]:
        lfm = get_lastfm_metadata(match["artist"], match["title"])
        metadata.update(lfm)
        artist_info = get_lastfm_artist_info(match["artist"])
        metadata.update(artist_info)
        print("Last.fm data fetched")

    # 5. Genius
    if match["artist"] and match["title"]:
        genius = get_genius_data(match["artist"], match["title"])
        metadata.update(genius)
        print("Genius data fetched")

    # 6. Genius lyrics
    if metadata.get("genius_url"):
        lyrics_data = get_genius_lyrics(metadata["genius_url"])
        if lyrics_data:
            metadata.update(lyrics_data)
            print("Lyrics scraped from Genius")

    cover = {}
    if metadata.get("release_id"):
        cover = get_cover_art(metadata["release_id"])
        print("Cover art data fetched")
        
    metadata.update(cover)

    return metadata

if __name__ == "__main__":
    if (len(sys.argv) < 2):
        print("Usage: python songInfo.py <audio_file>")
        sys.exit(1)

    filename = sys.argv[1]

    metadata = fetch_metadata(filename)

    out_path = f"{filename}_metadata.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(out_path)