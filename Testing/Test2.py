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
