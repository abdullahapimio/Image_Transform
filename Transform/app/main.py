from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict
from PIL import Image
import io
import requests
from google.cloud import storage
from google.cloud import tasks_v2
import json

app = FastAPI()

# Setup Google Cloud Storage
bucket_name = "image_transform"
storage_client = storage.Client()
bucket = storage_client.bucket(bucket_name)

# Google Cloud Tasks setup
project = 'apimio-ai'
queue = 'Image-queue'
location = 'asia-northeast1'
tasks_client = tasks_v2.CloudTasksClient()
parent = tasks_client.queue_path(project, location, queue)

WEBHOOK_SECRET = "apimiorocks123$"  # Your predefined secret token

class ImageURLs(BaseModel):
    urls: List[str]

def upload_to_gcs(image_buffer: io.BytesIO, file_name: str) -> str:
    """Uploads an image to Google Cloud Storage and returns the URL."""
    blob = bucket.blob(file_name)
    blob.upload_from_file(image_buffer, content_type='image/jpeg', rewind=True)
    return f"https://storage.googleapis.com/{bucket_name}/{file_name}"

def process_image(url: str) -> Dict:
    """Processes an image and uploads it to GCS, tracking success or failure."""
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
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        file_name = f"processed_{url.split('/')[-1]}"
        image_url = upload_to_gcs(buffer, file_name)
        return {"status": "success", "url": image_url}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

def create_task(image_url: str, image_id: int):
    """Creates a task for image processing with retry configurations."""
    payload = json.dumps({"url": image_url, "id": image_id})
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": "https://apimio-ai.an.r.appspot.com/process_image_task",
            "headers": {"Content-Type": "application/json"},
            "body": payload.encode()
        }
    }
    response = tasks_client.create_task(parent=parent, task=task)
    return response.name


@app.post("/webhook/acknowledge")
async def acknowledge_images(image_urls: ImageURLs):
    """Receives image URLs and queues them for processing."""
    for idx, url in enumerate(image_urls.urls):
        create_task(url, idx)
    return {"message": "Processing tasks have been queued", "task_count": len(image_urls.urls)}

@app.post("/process_image_task")
async def process_image_task(request: Request):
    """Processes images from tasks created by Google Cloud Tasks."""
    data = await request.json()
    result = process_image(data['url'])
    return result

@app.post("/webhook/deliver")
async def deliver_processed_images(request: Request):
    """Endpoint that checks token, retrieves processed image URLs from GCS, and delivers them."""
    data = await request.json()
    token = data.get("token")
    if token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid token")
    # Retrieve URLs of processed images directly from GCS
    images = []
    try:
        blobs = bucket.list_blobs(prefix="processed_")  # Modify the prefix as needed
        for blob in blobs:
            image_url = f"https://storage.googleapis.com/{bucket_name}/{blob.name}"
            images.append({"image_id": blob.name.split('_')[-1], "url": image_url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Send the processed image URLs to the external system's webhook URL
    response = requests.post(data['webhook_url'], json={"images": images, "token": token})
    if response.status_code == 200:
        return {"status": "ok", "message": "Processed images delivered"}
    else:
        raise HTTPException(status_code=response.status_code, detail="Failed to deliver images")

@app.get("/")
def read_root():
    return {"Hello": "World"}
