from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from typing import List, Dict
from PIL import Image
import io
import requests

app = FastAPI()

# Define the required criteria
REQUIRED_FORMATS = ["JPEG", "JPG", "WEBP"]
MAX_SIZE_KB = 200
MIN_DIMENSION = 1080
WEBHOOK_SECRET = "your_secret_token_here"  # Replace with your secret token

def process_image(url: str) -> Dict:
    try:
        response = requests.get(url)
        response.raise_for_status()

        image = Image.open(io.BytesIO(response.content))

        # Original details
        original_format = image.format
        original_size_kb = len(response.content) / 1024  # Size in KB
        original_dimensions = image.size

        # Convert image to RGB, if it's not and fill with white if it has transparency
        if image.mode in ("RGBA", "P"):
            # Create a white background
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3] if 'A' in image.mode else None)
            image = background
        else:
            image = image.convert("RGB")

        # Ensure image dimensions meet the minimum requirement
        width, height = image.size
        if width < MIN_DIMENSION or height < MIN_DIMENSION:
            scaling_factor = MIN_DIMENSION / min(width, height)
            image = image.resize((int(width * scaling_factor), int(height * scaling_factor)), Image.LANCZOS)

        buffer = io.BytesIO()
        quality = 85

        # Compress to meet size requirement and convert to JPEG regardless of original format
        image.save(buffer, format="JPEG", quality=quality)
        size_kb = buffer.getbuffer().nbytes / 1024
        while size_kb > MAX_SIZE_KB and quality > 10:
            buffer = io.BytesIO()
            quality -= 5
            image.save(buffer, format="JPEG", quality=quality)
            size_kb = buffer.getbuffer().nbytes / 1024

        new_dimensions = image.size

        return {
            "original_url": url,
            "original_format": original_format,
            "original_size_kb": original_size_kb,
            "original_dimensions": original_dimensions,
            "new_format": "JPEG",
            "new_size_kb": size_kb,
            "new_dimensions": new_dimensions,
            "processed_image": buffer
        }

    except Exception as e:
        return {"error": str(e)}

# Data model for image URLs
class ImageURLs(BaseModel):
    urls: List[str]

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/process_images")
async def process_images(urls: ImageURLs):
    results = {"processed_images": []}
    for url in urls.urls:
        result = process_image(url)
        if "processed_image" in result:
            result.pop("processed_image")  # Remove the buffer from the response
        results["processed_images"].append(result)
    return results

@app.get("/get_processed_image/")
async def get_processed_image(url: str):
    processed_image = process_image(url)
    if "error" in processed_image:
        raise HTTPException(status_code=400, detail=processed_image["error"])
    
    buffer = processed_image.get("processed_image")
    if buffer:
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="image/jpeg")
    else:
        raise HTTPException(status_code=404, detail="Processed image not available")

@app.post("/webhook/acknowledge")
async def acknowledge_images(request: Request):
    data = await request.json()
    if "urls" in data:
        return {"status": "ok", "message": "All images received"}
    else:
        raise HTTPException(status_code=400, detail="Invalid data")

@app.post("/webhook/deliver")
async def deliver_processed_images(request: Request):
    data = await request.json()
    webhook_url = data.get("webhook_url")
    token = data.get("token")
    processed_images = []
    
    if token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid token")

    if not webhook_url:
        raise HTTPException(status_code=400, detail="Webhook URL not provided")

    if "urls" in data:
        urls = data["urls"]
        for url in urls:
            result = process_image(url)
            if "processed_image" in result:
                processed_images.append({
                    "original_url": result["original_url"],
                    "processed_image_url": url  # Assuming processed image URL or similar identifier
                })

        response = requests.post(webhook_url, json={"images": processed_images, "token": WEBHOOK_SECRET})
        
        if response.status_code == 200:
            return {"status": "ok", "message": "Processed images delivered"}
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to deliver images")
    else:
        raise HTTPException(status_code=400, detail="No image URLs provided")
