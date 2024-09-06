import requests
import pytest

# URL of your FastAPI application
BASE_URL = "https://apimio-ai.an.r.appspot.com"

# List of image URLs to process
IMAGE_URLS = [
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/36_1.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/Untitleddesign_4.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/09.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/05_1af1a1ee-fee2-431c-bfdb-e4fb2cca535a.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/06_3640ea2a-3dfc-4ec5-8c71-3d58117482f7.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/Atenas-3176.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/Black-2260.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/Blindcornerblum_01_fe4e7ede-a9a4-4e9c-a0de-657b3c6ed8fa.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/Blindcornerblum_1_c8c03729-a1b6-4674-9bff-883a6994a0ad.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/Blindcornerblum_1.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/Blindcornerblum_01.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/Plate3mmBlum_01_168d5a27-eaf0-4495-91de-2998ad581085.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/Plate3mmBlum_df03d40b-498d-4854-a628-a0b8a5b2d6f4.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/63.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/64.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/cava_image-removebg-preview_2.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/cava_image-removebg-preview_2_d9dd543e-b26b-429c-9c58-d536d6e88a36.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/cic05_1085_quadro-syncron-registro_ANV-01-OAK.jpg",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/cic07_1085_quadro-syncron-registro_ANV-03_OAK.jpg",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/anniversary2-cava_ANV-2-OAK.jpg",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/cic08_1085_quadro-syncron-registro_CA-01.jpg",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/cic09_1085_quadro-syncron-registro_CA-02.jpg",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/cic10_1085_quadro-syncron-registro_CA-03.jpg",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/frappe1.jpg",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/frappe1-09-5-pieces.jpg"
]


def test_process_images():
    """Tests the /process_images endpoint by submitting a list of URLs and evaluating the response."""
    response = requests.post(
        f"{BASE_URL}/process_images",
        json={"urls": IMAGE_URLS},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    data = response.json()
    assert 'processed_images' in data
    assert len(data['processed_images']) == len(IMAGE_URLS)

    # Each item in the response should have certain keys
    for item in data['processed_images']:
        assert 'original_url' in item
        assert 'new_size_kb' in item
        assert 'new_dimensions' in item

def test_get_processed_image():
    """Tests the /get_processed_image/ endpoint for a single image retrieval."""
    # Test this for the first image in the list
    test_url = IMAGE_URLS[0]
    response = requests.get(f"{BASE_URL}/get_processed_image/", params={"url": test_url})
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'image/jpeg'  # Ensure this matches expected content type

# Run tests if this script is executed
if __name__ == "__main__":
    pytest.main()
