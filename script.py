import os ## need computer access
import face_recognition ## see step 1
import cv2 ## also step 1

## Since my folder is nearly 50Gbs big, I will not create a folder called unsorted photos. I will merely point the script to the folder

REFERENCE_FOLDER = "/Users/avi/Desktop/ReferencePhotos"
TARGET_FOLDER = "/Users/avi/Desktop/RoboticsPhotos"

# Dictionaries to store our known face data
known_face_encodings = []
known_face_names = []

VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")  # This fixes it!

print("Loading reference photos...")

for filename in os.listdir(REFERENCE_FOLDER):
    if filename.lower().endswith(VALID_EXTENSIONS):
        # 1. Get the base name (e.g., "Avi1" or "Avi_2")
        base_name = os.path.splitext(filename)[0]
        
        # 2. Strip out any numbers or underscores so "Avi1" or "Avi_1" just becomes "Avi"
        name = ''.join([i for i in base_name if i.isalpha()]).strip()
            
        img_path = os.path.join(REFERENCE_FOLDER, filename)
        try:
            ref_image = face_recognition.load_image_file(img_path)
            ref_encoding = face_recognition.face_encodings(ref_image)[0]
            
            # Append the encoding and the cleaned name
            known_face_encodings.append(ref_encoding)
            known_face_names.append(name)
            print(f"-> Learned a face profile for: {name}")
        except IndexError:
            print(f"!! No face found in reference file: {filename}")

# Let's count UNIQUE names using a Python 'set'
unique_people = len(set(known_face_names))
print(f"\nFinished loading references. Total unique people known: {unique_people}\n")

print("Starting 50GB scan across all subfolders...")

# 1. os.walk goes deep into your subfolders (2024, 2025, etc.)
for root, dirs, files in os.walk(TARGET_FOLDER):
    for filename in files:
        # Skip files that aren't images
        if not filename.lower().endswith(VALID_EXTENSIONS):
            continue
            
        # FIX: Use 'root' instead of TARGET_FOLDER so Python finds files deep inside subfolders
        file_path = os.path.join(root, filename)
        print(f"\nProcessing {filename}...")

        # FIX: Everything below is now properly indented inside the loop!
        try:
            # 2. Load the image from the 50GB library
            image = face_recognition.load_image_file(file_path)
            
            # 3. Find where the faces are, then calculate their math encodings
            face_locations = face_recognition.face_locations(image, model="hog")
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            print(f"-> Found {len(face_locations)} face(s) in this photo.")
            
            # 4. Loop through every single face found in this specific photo
            for mystery_face_encoding in face_encodings:
                
                # Compare the mystery face against ALL your reference photos
                # tolerance=0.6 is the standard. Lower = stricter, Higher = looser matching.
                matches = face_recognition.compare_faces(known_face_encodings, mystery_face_encoding, tolerance=0.6)
                
                name = "Unknown" # Default if no match is found
                
                # Check if we got any 'True' matches
                if True in matches:
                    # Find the index where 'True' is located (e.g., index 0)
                    first_match_index = matches.index(True)
                    # Look up the name at that same index
                    name = known_face_names[first_match_index]
                    
                    print(f" 🎉 MATCH FOUND: {name} is in {filename}!")
            
        except Exception as e:
            print(f"-> Could not process {filename}. Error: {e}")

print("\n Scan complete!")

# for root, dirs, files in os.walk(TARGET_FOLDER):
#     for filename in files:
#         if not filename.lower().endswith(VALID_EXTENSIONS): ## checking if the file is an image
#             continue ## skipping if not an image
    
#         file_path = os.path.join(TARGET_FOLDER, filename)
#         print(f"Processing {filename}...")

#     try:
#         image = face_recognition.load_image_file(file_path) ## loads the image.
        
#         face_locations = face_recognition.face_locations(image, model="hog")
#         print(f"-> Found {len(face_locations)} face(s) in this photo.")
        
#     except Exception as e:
#         print(f"-> Could not process {filename}. Error: {e}")