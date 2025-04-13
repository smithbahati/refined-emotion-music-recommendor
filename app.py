import cv2
import numpy as np
from tensorflow.keras.models import load_model
from flask import Flask, render_template, Response, jsonify, request, redirect, session
from flask_caching import Cache
import time
import logging
import atexit
from threading import Lock
import os
import gdown
from spotify_utils import (
    get_top_tracks_by_genre,
    EMOTION_GENRE_MAP,
    get_or_create_playlist,
    update_playlist,
    sp,
    play_playlist
)

app = Flask(__name__)
app.secret_key = '52c56ae18ac346a3868bdb537c313f53'  # Required for session management

def download_model():
    """Download the emotion detection model from Google Drive if it doesn't exist."""
    model_path = 'emotion_detect_models.h5'
    if not os.path.exists(model_path):
        logging.info("Downloading emotion detection model...")
        url = 'https://drive.google.com/file/d/1rYX33aT9IOr5aYdMaDLPK4u_B9Uw89z_/view?usp=sharing'
        try:
            gdown.download(url, model_path, quiet=False, fuzzy=True)
            logging.info("Model downloaded successfully!")
        except Exception as e:
            logging.error(f"Error downloading model: {str(e)}")
            raise Exception("Failed to download the emotion detection model.")
    return model_path

# Caching to optimize API calls
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# User feedback storage
user_feedback = {}
user_favorites = {}
skipped_tracks = {}

# Initialize webcam
video_capture = cv2.VideoCapture(0)

# Global variables for emotion detection
detected_emotion = "Waiting..."
last_emotion = None
last_update_time = time.time()
emotion_lock = Lock()

# Download and load the pre-trained emotion detection model
model_path = download_model()
model = load_model(model_path)

# Emotion mapping
EMOTIONS = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

# Setup logging
logging.basicConfig(level=logging.INFO)

# Ensure webcam is open
if not video_capture.isOpened():
    logging.error("❌ Webcam initialization failed.")
    exit(1)  # Exit if the webcam cannot be opened

# Release webcam when the app stops
def release_camera():
    video_capture.release()
    logging.info("🎥 Webcam released successfully.")

atexit.register(release_camera)

def predict_emotion(frame):
    """Predict emotion from a frame with confidence threshold."""
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)  # Adjusted parameters for better face detection
    
    for (x, y, w, h) in faces:
        # Draw rectangle around face
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        # Prepare face for emotion detection
        face_img = gray[y:y+h, x:x+w]
        face_img = cv2.resize(face_img, (48, 48))
        face_img = np.expand_dims(face_img, axis=0)
        face_img = np.expand_dims(face_img, axis=-1)
        face_img = face_img / 255.0
        
        # Predict emotion with confidence
        prediction = model.predict(face_img)[0]
        emotion_idx = np.argmax(prediction)
        confidence = prediction[emotion_idx]
        
        # Only return emotion if confidence is high enough
        if confidence > 0.5:  # Minimum 50% confidence required
            return EMOTIONS[emotion_idx], confidence
        else:
            return "Uncertain", 0.0
    
    return "No face detected", 0.0

def get_stable_emotion(new_emotion, confidence):
    """Ensure the emotion remains stable before updating using temporal smoothing."""
    global last_emotion, last_update_time, detected_emotion
    current_time = time.time()

    # Initialize state if needed
    if not hasattr(get_stable_emotion, 'emotion_history'):
        get_stable_emotion.emotion_history = []
        get_stable_emotion.confidence_history = []
        get_stable_emotion.last_valid_emotion = "Neutral"
        get_stable_emotion.stable_since = current_time
        get_stable_emotion.emotion_counts = {}

    # Maximum history length for temporal smoothing
    MAX_HISTORY = 10
    REQUIRED_CONSECUTIVE = 4  # Increased from 2 to 4 for better stability
    MIN_CONFIDENCE = 0.5     # Minimum confidence threshold
    
    # If no face detected or low confidence, maintain last valid emotion
    if new_emotion in ["No face detected", "Uncertain"] or confidence < MIN_CONFIDENCE:
        return get_stable_emotion.last_valid_emotion

    # Add new emotion to history
    get_stable_emotion.emotion_history.append(new_emotion)
    get_stable_emotion.confidence_history.append(confidence)
    
    # Keep history at maximum length
    if len(get_stable_emotion.emotion_history) > MAX_HISTORY:
        get_stable_emotion.emotion_history.pop(0)
        get_stable_emotion.confidence_history.pop(0)

    # Count emotions in history with their confidence weights
    emotion_scores = {}
    for emotion, conf in zip(get_stable_emotion.emotion_history, get_stable_emotion.confidence_history):
        emotion_scores[emotion] = emotion_scores.get(emotion, 0) + conf

    # Get the emotion with highest confidence-weighted count
    if emotion_scores:
        current_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
    else:
        current_emotion = get_stable_emotion.last_valid_emotion

    # Update consecutive counts
    if current_emotion not in get_stable_emotion.emotion_counts:
        get_stable_emotion.emotion_counts = {current_emotion: 1}
    else:
        get_stable_emotion.emotion_counts[current_emotion] += 1
        # Reset other emotion counts
        for emotion in list(get_stable_emotion.emotion_counts.keys()):
            if emotion != current_emotion:
                get_stable_emotion.emotion_counts[emotion] = 0

    # Check if emotion has been stable for enough consecutive frames
    if get_stable_emotion.emotion_counts.get(current_emotion, 0) >= REQUIRED_CONSECUTIVE:
        if current_time - get_stable_emotion.stable_since > 1.0:  # Minimum 1 second between emotion changes
            get_stable_emotion.last_valid_emotion = current_emotion
            get_stable_emotion.stable_since = current_time
            get_stable_emotion.emotion_counts.clear()
            return current_emotion
    
    return get_stable_emotion.last_valid_emotion

@app.route('/')
def index():
    """Render the main webpage."""
    return render_template('index.html')

def gen_frames():
    """Capture frames from webcam, detect emotion, and overlay text."""
    global detected_emotion
    frame_count = 0
    
    while True:
        if not video_capture.isOpened():
            logging.error("❌ Webcam is not accessible. Stopping frame capture.")
            break

        success, frame = video_capture.read()
        if not success:
            logging.error("❌ Failed to read frame from webcam.")
            continue

        frame_count += 1
        # Process every 2nd frame
        if frame_count % 2 == 0:
            # Predict emotion with confidence
            emotion, confidence = predict_emotion(frame)
            stable_emotion = get_stable_emotion(emotion, confidence)

            # Update emotion if it's different
            if detected_emotion != stable_emotion:
                with emotion_lock:
                    detected_emotion = stable_emotion
                    logging.info(f"🔄 Updated Emotion: {detected_emotion} (Confidence: {confidence:.2f})")

        # Overlay emotion text and confidence on the frame
        text_color = (0, 255, 0)  # Green color for the text
        bg_color = (0, 0, 0)      # Black background for better readability
        
        # Add background rectangle for text
        text = f"Current Emotion: {detected_emotion}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Draw background rectangle
        cv2.rectangle(frame, (10, 10), (20 + text_width, 20 + text_height), bg_color, -1)
        
        # Draw text
        cv2.putText(frame, text, (15, 30), font, font_scale, text_color, thickness)

        # Convert frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            logging.error("❌ Failed to encode frame.")
            continue

        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    """Stream video feed with real-time emotion detection."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_emotion', methods=['GET'])
@cache.cached(timeout=1)  # Reduced cache timeout to 1 second for more responsive updates
def get_emotion():
    """Return the latest detected emotion."""
    global detected_emotion
    with emotion_lock:
        current_emotion = detected_emotion
        
    # Convert to neutral only if waiting
    if current_emotion.lower() == "waiting...":
        return jsonify({"emotion": "neutral"})
        
    return jsonify({"emotion": current_emotion})

@app.route('/recommend', methods=['GET'])
@cache.cached(timeout=5)  # Cache recommendations for 5 seconds instead of 10
def recommend():
    """Update Spotify playlist and return recommendations based on detected emotion."""
    global detected_emotion

    with emotion_lock:
        current_emotion = str(detected_emotion).lower()  # Ensure valid string

    logging.info(f"Current Emotion in /recommend: {current_emotion}")

    # Check for invalid emotion states
    if current_emotion.lower() in ["waiting...", "no face detected"]:
        return jsonify({
            "success": False,
            "message": "Please ensure your face is visible to the camera."
        }), 400

    # Ensure emotion exists in Spotify mapping
    if current_emotion not in EMOTION_GENRE_MAP:
        logging.warning(f"Emotion '{current_emotion}' not in mapping. Using 'neutral' as default.")
        current_emotion = "neutral"

    try:
        # Get cached playlist ID if available
        playlist_id = cache.get('current_playlist_id')
        if not playlist_id:
            playlist_id = get_or_create_playlist()
            if playlist_id:
                cache.set('current_playlist_id', playlist_id, timeout=3600)  # Cache for 1 hour

        if not playlist_id:
            return jsonify({
                "success": False,
                "message": "Failed to retrieve or create playlist."
            }), 500

        # Get cached tracks for this emotion if available
        cache_key = f'tracks_{current_emotion}'
        tracks = cache.get(cache_key)
        
        if not tracks:
            tracks = update_playlist(playlist_id=playlist_id, emotion=current_emotion)
            if tracks:
                cache.set(cache_key, tracks, timeout=30)  # Cache tracks for 30 seconds

        if not tracks:
            return jsonify({
                "success": False,
                "message": f"Could not find suitable tracks for emotion: {current_emotion}"
            }), 404

        playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
        
        return jsonify({
            "success": True,
            "emotion": current_emotion,
            "message": f"🎵 Playlist updated with {current_emotion} tracks!",
            "spotify_playlist_url": playlist_url,
            "tracks": tracks
        })

    except Exception as e:
        logging.error(f"Error in recommend endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "message": "An error occurred while updating recommendations."
        }), 500

@app.route('/play', methods=['POST'])
def play():
    """Play a specific track on Spotify."""
    try:
        # Check if we received JSON data
        if not request.is_json:
            logging.error("No JSON data received in request")
            return jsonify({
                "success": False,
                "message": "Invalid request format"
            }), 400

        track_id = request.json.get('track_id')
        if not track_id:
            logging.error("No track ID provided")
            return jsonify({
                "success": False,
                "message": "No track ID provided"
            }), 400

        logging.info(f"Attempting to play track: {track_id}")

        # Get available devices
        try:
            devices = sp.devices()
            logging.info(f"Available devices: {devices}")
        except Exception as device_error:
            logging.error(f"Error getting devices: {str(device_error)}")
            return jsonify({
                "success": False,
                "message": "Error accessing Spotify. Please check if you're logged in and have a Premium account."
            }), 400

        if not devices or not devices.get('devices'):
            logging.error("No Spotify devices found")
            return jsonify({
                "success": False,
                "message": "No Spotify devices found. Please open Spotify on your device and ensure you're not in offline mode."
            }), 400

        # Log all available devices
        for device in devices['devices']:
            logging.info(f"Found device: {device['name']} (ID: {device['id']}, Active: {device.get('is_active', False)})")

        # Try to find an active device first, otherwise use the first available one
        active_device = next((d for d in devices['devices'] if d.get('is_active')), devices['devices'][0])
        device_id = active_device['id']
        device_name = active_device['name']

        logging.info(f"Selected device for playback: {device_name} (ID: {device_id})")

        # Start playback
        try:
            sp.start_playback(device_id=device_id, uris=[f'spotify:track:{track_id}'])
            logging.info(f"Successfully started playback on device: {device_name}")
            return jsonify({
                "success": True,
                "message": f"Playing on {device_name}"
            })
        except Exception as playback_error:
            error_message = str(playback_error)
            logging.error(f"Playback error: {error_message}")
            
            if "Premium required" in error_message:
                return jsonify({
                    "success": False,
                    "message": "Spotify Premium is required for playback control"
                }), 403
            elif "No active device found" in error_message:
                return jsonify({
                    "success": False,
                    "message": "Please open Spotify on your device and start playing any track first"
                }), 400
            else:
                return jsonify({
                    "success": False,
                    "message": f"Playback error: {error_message}"
                }), 500

    except Exception as e:
        logging.error(f"Unexpected error in play route: {str(e)}")
        return jsonify({
            "success": False,
            "message": "An unexpected error occurred"
        }), 500

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback for emotion detection and song recommendations."""
    try:
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "message": "No feedback data provided"
            }), 400

        user_id = session.get('user_id', 'anonymous')
        feedback_type = data.get('type')
        rating = data.get('rating')
        comment = data.get('comment')
        track_id = data.get('track_id')

        if not feedback_type or not rating:
            return jsonify({
                "success": False,
                "message": "Missing required feedback information"
            }), 400

        # Store feedback
        if user_id not in user_feedback:
            user_feedback[user_id] = []

        user_feedback[user_id].append({
            'type': feedback_type,
            'rating': rating,
            'comment': comment,
            'track_id': track_id,
            'timestamp': time.time()
        })

        return jsonify({
            "success": True,
            "message": "Feedback submitted successfully"
        })

    except Exception as e:
        logging.error(f"Error submitting feedback: {str(e)}")
        return jsonify({
            "success": False,
            "message": "An error occurred while submitting feedback"
        }), 500

@app.route('/get_tracks_info', methods=['POST'])
def get_tracks_info():
    """Get full track information for a list of track IDs."""
    try:
        data = request.json
        if not data or 'track_ids' not in data:
            return jsonify({
                "success": False,
                "message": "No track IDs provided"
            }), 400

        track_ids = data['track_ids']
        if not track_ids:
            return jsonify({
                "success": True,
                "tracks": []
            })

        # Get track details from Spotify
        tracks = []
        for track_id in track_ids:
            try:
                track = sp.track(track_id)
                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': ', '.join(artist['name'] for artist in track['artists']),
                    'album_cover': track['album']['images'][0]['url'] if track['album']['images'] else '',
                    'spotify_url': track['external_urls']['spotify']
                })
            except Exception as e:
                logging.error(f"Error fetching track {track_id}: {str(e)}")
                continue

        return jsonify({
            "success": True,
            "tracks": tracks
        })

    except Exception as e:
        logging.error(f"Error in get_tracks_info: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to fetch track information"
        }), 500

@app.route('/favorite', methods=['POST'])
def toggle_favorite():
    """Add or remove a track from user's favorites."""
    try:
        data = request.json
        if not data or 'track_id' not in data:
            return jsonify({
                "success": False,
                "message": "No track ID provided"
            }), 400

        user_id = session.get('user_id', 'anonymous')
        track_id = data['track_id']

        # Initialize user's favorites if not exists
        if 'favorites' not in session:
            session['favorites'] = []

        favorites = session['favorites']

        # Toggle favorite status
        if track_id in favorites:
            favorites.remove(track_id)
            is_favorite = False
        else:
            favorites.append(track_id)
            is_favorite = True

        # Update session
        session['favorites'] = favorites
        session.modified = True

        return jsonify({
            "success": True,
            "is_favorite": is_favorite,
            "message": "Track {} favorites".format("removed from" if not is_favorite else "added to")
        })

    except Exception as e:
        logging.error(f"Error toggling favorite: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to update favorites"
        }), 500

@app.route('/skip', methods=['POST'])
def skip_track():
    """Skip current track and log it for future reference."""
    try:
        data = request.json
        if not data or 'track_id' not in data:
            return jsonify({
                "success": False,
                "message": "No track ID provided"
            }), 400

        user_id = session.get('user_id', 'anonymous')
        track_id = data['track_id']

        # Log skipped track
        if user_id not in skipped_tracks:
            skipped_tracks[user_id] = set()
        skipped_tracks[user_id].add(track_id)

        # Skip to next track in Spotify
        try:
            sp.next_track()
            return jsonify({
                "success": True,
                "message": "Track skipped successfully"
            })
        except Exception as spotify_error:
            logging.error(f"Error skipping track in Spotify: {str(spotify_error)}")
            return jsonify({
                "success": False,
                "message": "Error skipping track. Please ensure Spotify is active."
            }), 400

    except Exception as e:
        logging.error(f"Error processing skip request: {str(e)}")
        return jsonify({
            "success": False,
            "message": "An error occurred while skipping the track"
        }), 500

@app.route('/get_user_data', methods=['GET'])
def get_user_data():
    """Get user's favorites and history."""
    try:
        user_id = session.get('user_id', 'anonymous')
        favorites = session.get('favorites', [])
        skipped = session.get('skipped_tracks', [])

        return jsonify({
            "success": True,
            "favorites": favorites,
            "skipped_tracks": skipped
        })

    except Exception as e:
        logging.error(f"Error retrieving user data: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to retrieve user data"
        }), 500

if __name__ == '__main__':
    app.run(debug=True) 