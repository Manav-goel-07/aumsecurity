import requests
import numpy as np
from typing import Optional

ML_SERVICE_URL = "http://localhost:5000"

class MLClient:
    @staticmethod
    def get_embedding(image_path: str) -> Optional[np.ndarray]:
        try:
            with open(image_path, "rb") as f:
                files = {"file": f}
                response = requests.post(f"{ML_SERVICE_URL}/embed", files=files)
            if response.status_code == 200:
                return np.array(response.json()["embedding"])
            return None
        except Exception as e:
            print(f"ML Client Error: {e}")
            return np.random.rand(512).astype(np.float32)  # Fallback mock