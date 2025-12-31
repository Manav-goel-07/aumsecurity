# test_face_detection.py - Tests face detection on your image
import face_recognition
import sys

# Update this path if your image is elsewhere (use raw string for Windows paths)
image_path = r'C:\Users\arun_\aumsecurity\backend\app\Random photo(1).jpg'

try:
    # Load image
    print("Loading image...")
    image = face_recognition.load_image_file(image_path)
    print(f"Image loaded successfully! Shape: {image.shape}")

    # Detect faces and generate encodings
    print("Detecting faces...")
    encodings = face_recognition.face_encodings(image)
    print(f"Encodings found: {len(encodings)}")

    if encodings:
        encoding = encodings[0]  # First face
        print(f"Encoding shape: {encoding.shape}")  # Should be (128,)
        print(f"First 5 values: {list(encoding[:5])}")  # Sample floats
        print("SUCCESS: Face detected and encoded!")
    else:
        print("NO FACE DETECTED: Try a clearer, front-facing portrait image.")
        print("Tips: Single person, good lighting, >100x100 pixels, JPG/PNG format.")

except FileNotFoundError:
    print(f"ERROR: Image not found at {image_path}")
    print("Check path: Run 'dir app\\*.jpg' to list files.")
except Exception as e:
    print(f"ERROR: {str(e)}")
    print("Full traceback:")
    import traceback
    traceback.print_exc()