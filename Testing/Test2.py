import requests
import json
import os

def validate_image(data):
    """
    Validates the processed image data against specified criteria.
    Returns True if the image meets all criteria, False otherwise.
    """
    if data['new_format'] not in ['JPEG', 'WEBP']:
        return False
    if data['new_size_kb'] >= 200:
        return False
    if data['new_dimensions'][0] < 1080 or data['new_dimensions'][1] < 1080:
        return False
    return True

def process_and_download_images():
    process_url = "https://apimio-ai.an.r.appspot.com/process_images"
    get_image_url = "https://apimio-ai.an.r.appspot.com/get_processed_image/"
    
    save_directory = "downloaded_images"
    os.makedirs(save_directory, exist_ok=True)
    
    image_urls = [
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/36_1.png",
    "https://apimio-media.s3.us-east-2.amazonaws.com/images/Untitleddesign_4.png"
    ]
    
    response = requests.post(process_url, json={"urls": image_urls}, headers={"Content-Type": "application/json"})
    print("JSON Response from /process_images saved")
    response_data = response.json()
    
    with open('processed_images_response.json', 'w') as file:
        json.dump(response_data, file, indent=4)
    
    if response.status_code == 200:
        processed_data = response_data.get('processed_images', [])
        
        for idx, img_data in enumerate(processed_data):
            if not validate_image(img_data):
                print(f"Image {idx} does not meet the criteria and will not be downloaded.")
                continue
            
            img_url = img_data['original_url']
            img_response = requests.get(f"{get_image_url}?url={img_url}")
            
            if img_response.status_code == 200:
                image_path = os.path.join(save_directory, f'processed_image_{idx}.jpg')
                with open(image_path, 'wb') as f:
                    f.write(img_response.content)
            else:
                print(f"Failed to download image {idx}")

if __name__ == "__main__":
    process_and_download_images()
