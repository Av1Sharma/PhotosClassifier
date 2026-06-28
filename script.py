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

print("Loading reference photos...")

for filename in os.listdir(REFERENCE_FOLDER):
    if filename.lower().endswith(VALID_EXTENSIONS):
        # 1. Get the person's name by removing the file extension (e.g., "Tony_Stark.jpg" -> "Tony_Stark")
        name = os.path.splitext(filename)[0].replace("_", " ") 
        
        # 2. Get the full path to the reference image
        img_path = os.path.join(REFERENCE_FOLDER, filename)
        
        try:
            # 3. Load the image file
            ref_image = face_recognition.load_image_file(img_path)
            
            # 4. Get the face encoding (the math profile of the face)
            # We take index [0] because we assume there is only 1 face in a reference photo
            ref_encoding = face_recognition.face_encodings(ref_image)[0]
            
            # 5. Save them into our lists
            known_face_encodings.append(ref_encoding)
            known_face_names.append(name)
            
            print(f"-> Successfully learned the face of: {name}")
            
        except IndexError:
            print(f"!! Warning: Could not find a clear face in {filename}. Make sure it's well-lit.")
        except Exception as e:
            print(f"!! Error processing {filename}: {e}")

print(f"\nFinished loading references. Total people known: {len(known_face_names)}")

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