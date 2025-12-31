from flask import Flask, request, jsonify
import cv2
import numpy as np
import os
from insightface.app import FaceAnalysis
import traceback

app = Flask(__name__)

# Initialize InsightFace (downloads models on first run; use CPU for simplicity)
# buffalo_l: High-accuracy model for 512-dim embeddings (good for cross-image matching)
face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0, det_size=(640, 640))  # det_size: Balance speed/accuracy (640x640 recommended)

@app.route('/embed', methods=['POST'])
def get_embedding():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save temp file for processing (Windows-friendly path)
    temp_path = os.path.join(os.getcwd(), f"temp_{file.filename}")
    file.save(temp_path)
    
    try:
        # Load and process image with OpenCV
        img = cv2.imread(temp_path)
        if img is None:
            return jsonify({'error': 'Invalid or corrupted image file'}), 400
        
        print(f"Loading image... Shape: {img.shape}")
        
        # Detect faces and extract embedding
        faces = face_app.get(img)
        print(f"Detecting faces... Encodings found: {len(faces)}")
        
        if not faces:
            return jsonify({'error': 'No face detected in the image. Use a clear, front-facing photo.'}), 400
        
        # Use the first (largest/most confident) face; extend for multi-face if needed
        embedding = faces[0].embedding  # Shape: (512,)
        print(f"Encoding shape: {embedding.shape}")
        print(f"First 5 values: {embedding[:5]}")  # Debug log
        
        return jsonify({
            'embedding': embedding.tolist(),  # Convert to list for JSON
            'shape': len(embedding),
            'success': True
        })
    
    except Exception as e:
        print(f"Error during embedding extraction: {traceback.format_exc()}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500
    
    finally:
        # Cleanup temp file to avoid disk clutter
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ML Service Running', 
        'model': 'InsightFace buffalo_l (512-dim embeddings)',
        'det_size': (640, 640),
        'providers': ['CPUExecutionProvider']
    })

if __name__ == '__main__':
    print("Starting ML Service on http://localhost:5001")
    print("First run may take time to download models (~300MB)...")
    app.run(host='0.0.0.0', port=5001, debug=True)  # Port 5001 to match backend; debug=True for dev