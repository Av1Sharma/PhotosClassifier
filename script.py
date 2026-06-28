import os ## need computer access
import face_recognition ## see step 1
import cv2 ## also step 1

## Since my folder is nearly 50Gbs big, I will not create a folder called unsorted photos. I will merely point the script to the folder

REFERENCE_FOLDER = "/Users/avi/Desktop/ReferencePhotos"
TARGET_FOLDER = "/Users/avi/Desktop/RoboticsPhotos"

# Dictionaries to store our known face data
known_face_encodings = []
known_face_names = []

VALID_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]

for root, dirs, files in os.walk(TARGET_FOLDER):
    for filename in files:
        if not filename.lower().endswith(VALID_EXTENSIONS): ## checking if the file is an image
            continue ## skipping if not an image
    
        file_path = os.path.join(TARGET_FOLDER, filename)
        print(f"Processing {filename}...")

    try:
        image = face_recognition.load_image_file(file_path) ## loads the image.
        
        face_locations = face_recognition.face_locations(image, model="hog")
        print(f"-> Found {len(face_locations)} face(s) in this photo.")
        
    except Exception as e:
        print(f"-> Could not process {filename}. Error: {e}")