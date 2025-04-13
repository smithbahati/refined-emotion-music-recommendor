import spotipy
import random
import logging
from spotipy.oauth2 import SpotifyOAuth

# Configure logging
logging.basicConfig(level=logging.INFO)

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="52c56ae18ac346a3868bdb537c313f53",
    client_secret="a5df4992dcd34222b17cff6151d47510",
    redirect_uri="http://127.0.0.1:8888",
    scope="playlist-modify-public user-read-private user-library-read user-read-playback-state user-modify-playback-state"
))

# 🎵 Emotion-to-Genre Mapping
EMOTION_GENRE_MAP = {
    "happy": "pop",
    "sad": "indie",
    "angry": "rock",
    "disgusted": "metal",  # Fixed invalid genre
    "fear": "electronic",
    "surprise": "jazz",
    "neutral": "chillout"  # Fixed invalid genre
}

# 🎧 Function to Get Top Tracks by Genre
def get_top_tracks_by_genre(genre, track_limit=10, exclude_tracks=set()):
    """Fetches songs for a given genre, ensuring diversity (1 song per artist)."""
    try:
        search_results = sp.search(q=f"genre:{genre}", type="track", limit=50)
        tracks = []
        artist_seen = set()

        for track in search_results.get("tracks", {}).get("items", []):
            artist_name = track["artists"][0]["name"]
            track_id = track["id"]

            # Ensure diversity: 1 song per artist & avoid duplicates
            if artist_name not in artist_seen and track_id not in exclude_tracks:
                tracks.append({
                    "id": track_id,
                    "name": track["name"],
                    "artist": artist_name,
                    "album_cover": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
                    "spotify_url": track["external_urls"]["spotify"]
                })
                artist_seen.add(artist_name)
                exclude_tracks.add(track_id)

            if len(tracks) >= track_limit:
                break

        random.shuffle(tracks)  # Shuffle for better variety
        return tracks if tracks else None
    except Exception as e:
        logging.error(f" Error fetching tracks: {e}")
        return None

# 🎵 Function to Get or Create a Playlist
def get_or_create_playlist():
    """Check if a playlist already exists before creating a new one."""
    user_id = sp.current_user()["id"]
    playlist_name = "Emotion-Based Playlist"
    
    # Check existing playlists
    existing_playlists = sp.current_user_playlists().get("items", [])
    for playlist in existing_playlists:
        if playlist["name"] == playlist_name:
            return playlist["id"]  # Return existing playlist
    
    # If not found, create a new one
    new_playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True)
    return new_playlist["id"]


# 🎶 Function to Update Playlist with New Songs
def update_playlist(playlist_id, emotion):
    """Updates the playlist with new songs based on detected emotion."""
    genre = EMOTION_GENRE_MAP.get(emotion.lower(), "pop")  # Ensure lowercase match
    tracks = get_top_tracks_by_genre(genre, track_limit=10)  # Increased track limit

    if not tracks:
        logging.warning(f" No tracks found for emotion: {emotion}, trying default genre.")
        tracks = get_top_tracks_by_genre("pop", track_limit=10)  # Try fallback

    if not tracks:
        logging.error("Still no tracks found. Skipping playlist update.")
        return None

    track_uris = [f"spotify:track:{track['id']}" for track in tracks]

    try:
        sp.playlist_replace_items(playlist_id=playlist_id, items=track_uris)
        logging.info(f"Updated playlist {playlist_id} with {len(track_uris)} tracks.")
        return tracks
    except Exception as e:
        logging.error(f"Error updating playlist: {e}")
        return None

# ▶️ Function to Start Playback on Spotify
def play_playlist(playlist_id):
    """Starts playing the updated playlist on the user's active device."""
    try:
        devices = sp.devices().get("devices", [])
        if not devices:
            logging.warning(" No active Spotify devices found.")
            return None

        device_id = devices[0]["id"]  # Select the first available device
        sp.start_playback(device_id=device_id, context_uri=f"spotify:playlist:{playlist_id}")
        logging.info(f"▶️ Playing playlist: {playlist_id} on device: {device_id}")
        return True
    except Exception as e:
        logging.error(f"Error playing playlist: {e}")
        return None
    

