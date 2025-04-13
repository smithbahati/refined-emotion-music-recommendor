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
    "happy": {
        "genres": ["pop", "dance pop", "happy", "funk"],
        "seed_genres": ["pop", "dance", "disco"],
        "target_valence": 0.8,
        "target_energy": 0.8,
        "min_valence": 0.6
    },
    "sad": {
        "genres": ["indie", "acoustic", "piano", "sad"],
        "seed_genres": ["acoustic", "piano", "indie"],
        "target_valence": 0.3,
        "target_energy": 0.4,
        "max_valence": 0.4
    },
    "angry": {
        "genres": ["rock", "metal", "punk", "hard-rock"],
        "seed_genres": ["rock", "metal"],
        "target_valence": 0.4,
        "target_energy": 0.9,
        "min_energy": 0.7
    },
    "disgusted": {
        "genres": ["metal", "industrial", "hardcore"],
        "seed_genres": ["metal", "industrial"],
        "target_valence": 0.3,
        "target_energy": 0.9,
        "min_energy": 0.7
    },
    "fear": {
        "genres": ["electronic", "ambient", "dark"],
        "seed_genres": ["ambient", "electronic"],
        "target_valence": 0.3,
        "target_energy": 0.5,
        "max_valence": 0.5
    },
    "surprise": {
        "genres": ["jazz", "funk", "electronic"],
        "seed_genres": ["jazz", "funk"],
        "target_valence": 0.6,
        "target_energy": 0.7,
        "min_energy": 0.5
    },
    "neutral": {
        "genres": ["chill", "ambient", "lofi", "study"],
        "seed_genres": ["chill", "study music"],
        "target_valence": 0.5,
        "target_energy": 0.5,
        "min_valence": 0.3,
        "max_valence": 0.7
    }
}

# Cache for recently recommended tracks per emotion
_recent_tracks_cache = {}

# 🎧 Function to Get Top Tracks by Genre
def get_top_tracks_by_genre(emotion_config, track_limit=15):
    """Fetches songs based on emotion configuration, ensuring diversity."""
    try:
        genres = emotion_config["genres"]
        seed_genres = emotion_config["seed_genres"]
        
        # Get recently played tracks for this emotion
        cache_key = "_".join(seed_genres)
        recent_tracks = _recent_tracks_cache.get(cache_key, set())
        
        tracks = []
        artist_seen = set()
        
        # First try recommendations API
        try:
            recommendations = sp.recommendations(
                seed_genres=seed_genres[:3],  # Spotify allows max 5 seed genres
                limit=50,
                target_valence=emotion_config.get("target_valence", 0.5),
                target_energy=emotion_config.get("target_energy", 0.5),
                min_valence=emotion_config.get("min_valence", 0.0),
                max_valence=emotion_config.get("max_valence", 1.0),
                min_energy=emotion_config.get("min_energy", 0.0),
                max_energy=emotion_config.get("max_energy", 1.0)
            )
            
            if recommendations and recommendations.get("tracks"):
                for track in recommendations["tracks"]:
                    if len(tracks) >= track_limit:
                        break
                        
                    track_id = track["id"]
                    artist_name = track["artists"][0]["name"]
                    
                    # Skip if we've seen this artist or track recently
                    if artist_name in artist_seen or track_id in recent_tracks:
                        continue
                        
                    tracks.append({
                        "id": track_id,
                        "name": track["name"],
                        "artist": artist_name,
                        "album_cover": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
                        "spotify_url": track["external_urls"]["spotify"]
                    })
                    
                    artist_seen.add(artist_name)
                    recent_tracks.add(track_id)
        except Exception as rec_error:
            logging.error(f"Error getting recommendations: {rec_error}")
        
        # If we still need more tracks, try search API
        if len(tracks) < track_limit:
            for genre in genres:
                if len(tracks) >= track_limit:
                    break
                    
                try:
                    results = sp.search(q=f"genre:{genre}", type="track", limit=50)
                    
                    if not results or not results["tracks"]["items"]:
                        continue
                        
                    for track in results["tracks"]["items"]:
                        if len(tracks) >= track_limit:
                            break
                            
                        track_id = track["id"]
                        artist_name = track["artists"][0]["name"]
                        
                        if artist_name in artist_seen or track_id in recent_tracks:
                            continue
                            
                        tracks.append({
                            "id": track_id,
                            "name": track["name"],
                            "artist": artist_name,
                            "album_cover": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
                            "spotify_url": track["external_urls"]["spotify"]
                        })
                        
                        artist_seen.add(artist_name)
                        recent_tracks.add(track_id)
                        
                except Exception as search_error:
                    logging.error(f"Error searching for tracks with genre '{genre}': {search_error}")
                    continue
        
        # Update recent tracks cache
        _recent_tracks_cache[cache_key] = recent_tracks
        
        # If cache gets too large, clear oldest entries
        if len(_recent_tracks_cache) > 7:
            oldest_key = next(iter(_recent_tracks_cache))
            del _recent_tracks_cache[oldest_key]
            
        random.shuffle(tracks)  # Shuffle for variety
        return tracks

    except Exception as e:
        logging.error(f"Error in get_top_tracks_by_genre: {e}")
        return None

# 🎵 Function to Get or Create a Playlist
def get_or_create_playlist():
    """Check if a playlist already exists before creating a new one."""
    try:
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
    except Exception as e:
        logging.error(f"Error in get_or_create_playlist: {e}")
        return None

# 🎶 Function to Update Playlist with New Songs
def update_playlist(playlist_id, emotion):
    """Updates the playlist with new songs based on detected emotion."""
    try:
        emotion = emotion.lower()
        if emotion not in EMOTION_GENRE_MAP:
            logging.warning(f"Unknown emotion: {emotion}, defaulting to neutral")
            emotion = "neutral"
            
        emotion_config = EMOTION_GENRE_MAP[emotion]
        tracks = get_top_tracks_by_genre(emotion_config, track_limit=15)

        if not tracks:
            logging.warning(f"No tracks found for emotion: {emotion}")
            return None

        track_uris = [f"spotify:track:{track['id']}" for track in tracks]
        
        try:
            sp.playlist_replace_items(playlist_id=playlist_id, items=track_uris)
            logging.info(f"Updated playlist {playlist_id} with {len(track_uris)} tracks for emotion: {emotion}")
            return tracks
        except Exception as e:
            logging.error(f"Error updating playlist: {e}")
            return None

    except Exception as e:
        logging.error(f"Error in update_playlist: {e}")
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