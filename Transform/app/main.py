from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict
from PIL import Image
import io
import requests
import json
import uuid
from google.cloud import storage, tasks_v2, firestore

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

# Initialize Firestore client
db = firestore.Client()

WEBHOOK_SECRET = "apimiorocks123$"  # Your predefined secret token

class ImageURLs(BaseModel):
    urls: List[str]

def upload_to_gcs(image_buffer: io.BytesIO, batch_id: str, file_name: str) -> str:
    """Uploads an image to Google Cloud Storage inside a folder named after the batch ID and returns the URL."""
    folder_path = f"{batch_id}/{file_name}"
    blob = bucket.blob(folder_path)
    blob.upload_from_file(image_buffer, content_type='image/jpeg', rewind=True)
    return f"https://storage.googleapis.com/{bucket_name}/{folder_path}"

def process_image(url: str, batch_id: str) -> Dict:
    """Processes an image, uploads it to GCS inside the batch folder, tracking success or failure."""
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
        image_url = upload_to_gcs(buffer, batch_id, file_name)
        return {"status": "success", "url": image_url}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

def create_batch(images):
    """Creates a new batch in Firestore and returns the batch ID."""
    batch_id = str(uuid.uuid4())
    batch_ref = db.collection('batches').document(batch_id)
    batch_ref.set({'status': 'processing', 'created_at': firestore.SERVER_TIMESTAMP})
    
    images_ref = batch_ref.collection('images')
    for idx, url in enumerate(images):
        images_ref.document(f'image_{idx}').set({
            'url': url,
            'status': 'queued'
        })

    return batch_id

@app.post("/webhook/acknowledge")
async def acknowledge_images(image_urls: ImageURLs):
    """Receives image URLs, creates a batch, and queues them for processing."""
    batch_id = create_batch(image_urls.urls)
    for idx, url in enumerate(image_urls.urls):
        create_task(url, idx, batch_id)
    return {"message": "Processing tasks have been queued", "batch_id": batch_id, "task_count": len(image_urls.urls)}

def create_task(image_url: str, image_id: int, batch_id: str):
    """Creates a task for image processing with batch details."""
    payload = json.dumps({"url": image_url, "id": image_id, "batch_id": batch_id})
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

@app.post("/process_image_task")
async def process_image_task(request: Request):
    """Processes images from tasks created by Google Cloud Tasks."""
    data = await request.json()
    result = process_image(data['url'], data['batch_id'])
    update_image_status(data['batch_id'], data['id'], 'completed' if result['status'] == 'success' else 'failed', result.get('url'))
    return result

def update_image_status(batch_id, image_id, status, processed_url=None):
    """Updates the status of a specific image within a batch and checks batch completion."""
    image_ref = db.collection('batches').document(batch_id).collection('images').document(f'image_{image_id}')
    update_data = {'status': status}
    if processed_url:
        update_data['processed_url'] = processed_url
    image_ref.update(update_data)
    check_batch_completion(batch_id)

def check_batch_completion(batch_id):
    """Checks if all images in a batch are processed and sends a notification if true."""
    batch_ref = db.collection('batches').document(batch_id)
    images_ref = batch_ref.collection('images')
    docs = images_ref.stream()

    all_completed = True
    for doc in docs:
        if doc.to_dict().get('status') != 'completed':
            all_completed = False
            break

    if all_completed:
        batch_ref.update({'status': 'completed'})
        notify_external_system(batch_id)

def notify_external_system(batch_id):
    """Sends a notification to an external system that a batch has been processed."""
    notification_url = "https://webhook.site/4fe1ccbd-82c5-4da4-85a4-17dc73eea3ed"  # Replace with actual notification URL
    response = requests.post(notification_url, json={"batch_id": batch_id, "status": "completed"})
    print(f"Notification sent with response: {response.status_code}, {response.text}")

@app.post("/webhook/deliver")
async def deliver_processed_images(request: Request):
    """Endpoint that checks token, retrieves processed image URLs from GCS, and delivers them."""
    data = await request.json()
    token = data.get("token")
    if token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid token")
    images = []
    try:
        blobs = bucket.list_blobs(prefix=f"{data['batch_id']}/processed_")  # Use the batch ID in the prefix
        for blob in blobs:
            image_url = f"https://storage.googleapis.com/{bucket_name}/{blob.name}"
            images.append({"image_id": blob.name.split('/')[-1], "url": image_url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    response = requests.post(data['webhook_url'], json={"images": images, "token": token})
    if response.status_code == 200:
        return {"status": "ok", "message": "Processed images delivered"}
    else:
        raise HTTPException(status_code=response.status_code, detail="Failed to deliver images")

@app.get("/")
def read_root():
    return {"Hello": "World"}
