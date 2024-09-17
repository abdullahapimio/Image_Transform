from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from typing import List, Dict
from PIL import Image
import io
import requests
from google.cloud import storage

app = FastAPI()

# Google Cloud Storage setup
bucket_name = "image_transform"
storage_client = storage.Client()
bucket = storage_client.bucket(bucket_name)

# Define the required criteria
REQUIRED_FORMATS = ["JPEG", "JPG", "WEBP"]
MAX_SIZE_KB = 200
MIN_DIMENSION = 1080
WEBHOOK_SECRET = "apimiorocks123$"  # Replace with your actual secret token

def upload_to_gcs(image_buffer: io.BytesIO, file_name: str) -> str:
    """Uploads an image to Google Cloud Storage and returns the URL."""
    blob = bucket.blob(file_name)
    blob.upload_from_file(image_buffer, content_type='image/jpeg', rewind=True)
    return f"https://storage.googleapis.com/{bucket_name}/{file_name}"

def download_from_gcs(file_name: str) -> io.BytesIO:
    """Downloads an image from Google Cloud Storage and returns it as a BytesIO buffer."""
    blob = bucket.blob(file_name)
    image_buffer = io.BytesIO()
    blob.download_to_file(image_buffer)
    image_buffer.seek(0)
    return image_buffer

def process_image(url: str) -> Dict:
    try:
        response = requests.get(url)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))

        if image.mode in ("RGBA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3] if 'A' in image.mode else None)
            image = background
        else:
            image = image.convert("RGB")

        width, height = image.size
        if width < MIN_DIMENSION or height < MIN_DIMENSION:
            scaling_factor = MIN_DIMENSION / min(width, height)
            image = image.resize((int(width * scaling_factor), int(height * scaling_factor)), Image.LANCZOS)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        file_name = f"processed_{url.split('/')[-1]}"
        image_url = upload_to_gcs(buffer, file_name)
        return {
            "original_url": url,
            "processed_image_url": image_url
        }

    except Exception as e:
        return {"error": str(e)}

class ImageURLs(BaseModel):
    urls: List[str]

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/webhook/acknowledge")
async def acknowledge_images(request: Request):
    data = await request.json()
    urls = data.get("urls", [])
    if urls:
        # This endpoint now simply acknowledges receipt of URLs.
        # Processing would be triggered separately or through a queue.
        return {"status": "ok", "message": "All images received"}
    else:
        raise HTTPException(status_code=400, detail="No URLs provided")

@app.post("/process_images")
async def process_images(urls: ImageURLs):
    results = []
    for url in urls.urls:
        result = process_image(url)
        results.append(result)
    return {"processed_images": results}

@app.get("/get_processed_image/")
async def get_processed_image(file_name: str):
    try:
        buffer = download_from_gcs(file_name)
        return StreamingResponse(buffer, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/webhook/deliver")
async def deliver_processed_images(request: Request):
    data = await request.json()
    webhook_url = data.get("webhook_url")
    token = data.get("token")
    urls = data.get("urls", [])
    processed_images = [process_image(url) for url in urls]

    response = requests.post(webhook_url, json={"images": processed_images, "token": WEBHOOK_SECRET})
    if response.status_code == 200:
        return {"status": "ok", "message": "Processed images delivered"}
    else:
        raise HTTPException(status_code=response.status_code, detail="Failed to deliver images")
