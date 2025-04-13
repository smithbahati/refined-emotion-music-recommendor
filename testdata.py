import cv2
import numpy as np
from keras.models import load_model

# Load the trained model
model = load_model('emotion_detect_models.h5')

# Load the Haar Cascade for face detection
faceDetect = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Define labels for emotions
labels_dict = {0: 'Angry', 1: 'Disgust', 2: 'Fear', 3: 'Happy', 4: 'Neutral', 5: 'Sad', 6: 'Surprise'}

# List of image paths to process
image_files = [
    r"C:\Users\smith\Desktop\final project\music-recommendation-main\testpics\angry.jpg",
    r"C:\Users\smith\Desktop\final project\music-recommendation-main\testpics\disgusted6.jpg",
    r"C:\Users\smith\Desktop\final project\music-recommendation-main\testpics\fear.jpg",
    r"C:\Users\smith\Desktop\final project\music-recommendation-main\testpics\happy.jpg",
    r"C:\Users\smith\Desktop\final project\music-recommendation-main\testpics\neutral.jpg",
    r"C:\Users\smith\Desktop\final project\music-recommendation-main\testpics\sad.jpg",
    r"C:\Users\smith\Desktop\final project\music-recommendation-main\testpics\sad2.jpg",
    r"C:\Users\smith\Desktop\final project\music-recommendation-main\testpics\surprised.jpg"
]

# Process each image
for image_file in image_files:
    # Read the image
    frame = cv2.imread(image_file)
    
    if frame is None:
        print(f"Error: Unable to load image {image_file}")
        continue  # Skip to the next image if loading fails

    # Convert the image to grayscale for face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces in the image
    faces = faceDetect.detectMultiScale(gray, 1.3, 3)
    
    for x, y, w, h in faces:
        # Extract the face region
        sub_face_img = gray[y:y+h, x:x+w]
        
        # Resize and normalize the face region
        resized = cv2.resize(sub_face_img, (48, 48))
        normalize = resized / 255.0
        reshaped = np.reshape(normalize, (1, 48, 48, 1))
        
        # Predict the emotion
        result = model.predict(reshaped)
        label = np.argmax(result, axis=1)[0]
        
        # Print the emotion label
        print(f"Detected emotion in {image_file}: {labels_dict[label]}")
        
        # Draw rectangles and label the detected face
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 1)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 255), 2)
        cv2.rectangle(frame, (x, y-40), (x+w, y), (50, 50, 255), -1)
        cv2.putText(frame, labels_dict[label], (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # Show the processed frame
    cv2.imshow(f"Frame: {image_file}", frame)
    cv2.waitKey(0)

# Destroy all OpenCV windows
cv2.destroyAllWindows()
