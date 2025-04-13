import cv2
import numpy as np
from tensorflow.keras.models import load_model
from mtcnn import MTCNN

# 1. Load the trained emotion detection model
try:
    emotion_model = load_model('emotion_detect_models.h5')
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    exit()

# 2. Define emotion labels (ensure this matches the training order)
emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
print(f"Emotion labels: {emotion_labels}")

# 3. Initialize the webcam
cap = cv2.VideoCapture(0)  # 0 refers to the default webcam
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

# 4. Initialize MTCNN face detector
detector = MTCNN()

while True:
    # Capture a frame from the webcam
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame.")
        break

    # 5. Detect faces using MTCNN
    try:
        faces = detector.detect_faces(frame)
    except Exception as e:
        print(f"Error in face detection: {e}")
        faces = []

    # 6. Process each detected face
    for face in faces:
        # Extract the bounding box coordinates
        x, y, w, h = face['box']
        # Ensure coordinates are valid
        x, y = max(0, x), max(0, y)  # Prevent negative coordinates
        w, h = min(w, frame.shape[1] - x), min(h, frame.shape[0] - y)  # Prevent out-of-bounds

        # Extract the face region
        face_roi = frame[y:y + h, x:x + w]
        if face_roi.size == 0:
            print("Warning: Empty face region detected.")
            continue

        # Convert to grayscale for the model
        face_roi_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)

        # 7. Preprocess the face for the model
        try:
            # Resize to 48x48 (assuming this is the input size of your model)
            resized_face = cv2.resize(face_roi_gray, (48, 48))
            # Normalize pixel values to [0, 1]
            normalized_face = resized_face / 255.0
            # Reshape for the model (1, 48, 48, 1)
            reshaped_face = np.reshape(normalized_face, (1, 48, 48, 1))

            # 8. Predict the emotion
            emotion_prediction = emotion_model.predict(reshaped_face, verbose=0)
            # Debug: Print the raw prediction scores
            print(f"Raw prediction scores: {emotion_prediction[0]}")
            print(f"Sum of probabilities: {np.sum(emotion_prediction[0]):.2f}")

            # Get the top predicted emotion and its confidence
            max_index = np.argmax(emotion_prediction[0])
            predicted_emotion = emotion_labels[max_index]
            confidence = emotion_prediction[0][max_index]

            # 9. Draw the bounding box and label on the frame
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Green rectangle
            label = f'{predicted_emotion} ({confidence:.2f})'
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

        except Exception as e:
            print(f"Error processing face: {e}")
            continue

    # 10. Display the processed frame
    cv2.imshow('Real-time Emotion Detection', frame)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 11. Release resources and close windows
cap.release()
cv2.destroyAllWindows()
print("Application closed.")