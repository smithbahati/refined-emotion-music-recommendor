# Emotion-Based Music Recommendation System

A real-time emotion detection system that recommends music from Spotify based on your current emotional state. The application uses computer vision and deep learning to detect emotions from facial expressions and creates personalized playlists that match your mood.

## Features

- Real-time emotion detection through webcam
- Automatic Spotify playlist generation based on detected emotions
- Favorites system for tracking preferred songs
- History tracking of played songs
- Light/dark mode support
- Keyboard shortcuts for quick access
- Search and filter functionality
- Recently played tracks section

## Prerequisites

- Python 3.7 or higher
- Webcam
- Spotify Premium account
- Internet connection

## Installation

1. Clone the repository:
```bash
git clone [your-repository-url]
cd detect
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. The emotion detection model will be automatically downloaded from Google Drive when you first run the application. The model file is approximately 600MB.

## Configuration

1. Set up your Spotify API credentials:
   - Create an application in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Set the redirect URI to `http://127.0.0.1:8888`
   - Update the `spotify_utils.py` file with your credentials

## Running the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

## Keyboard Shortcuts

- `F` - Open Favorites
- `H` - Open History
- `Esc` - Close panels
- `Space` - Play/pause
- `Alt + Right Arrow` - Skip track
- `L` - Toggle light/dark mode

## Features

### Emotion Detection
- Real-time facial emotion detection
- Support for 7 different emotions: Angry, Disgust, Fear, Happy, Neutral, Sad, Surprise
- Confidence threshold for accurate detection

### Music Recommendations
- Automatic playlist generation based on emotional state
- Genre mapping for each emotion
- Spotify Premium integration for playback control

### User Interface
- Clean, modern design
- Responsive layout
- Light/dark mode support
- Side panel for favorites and history
- Search and filter functionality
- Recently played tracks section

## Technical Details

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Flask (Python)
- **Emotion Detection**: TensorFlow, OpenCV
- **Music Integration**: Spotify Web API
- **Model**: Pre-trained CNN for emotion detection (automatically downloaded ~600MB)

## Troubleshooting

1. **Model Download Issues**
   - Ensure you have a stable internet connection
   - Check if you have sufficient disk space (~600MB required)
   - Try manually downloading the model from the provided Google Drive link

2. **Webcam Issues**
   - Ensure your webcam is properly connected
   - Grant browser permissions for camera access
   - Check if other applications are using the webcam

3. **Spotify Playback Issues**
   - Ensure you have a Spotify Premium account
   - Keep Spotify open on your device
   - Check if you're logged in to the correct account

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Your chosen license]

## Acknowledgments

- Emotion detection model based on [relevant papers/repositories]
- Spotify Web API for music integration
- Flask framework for web application
- OpenCV for image processing 