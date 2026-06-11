import os
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.getenv("CLOUDINARY_API_KEY", ""),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
)


def upload_media(file_bytes: bytes, resource_type: str = "image", folder: str = "pod") -> str:
    """Upload image or video bytes to Cloudinary; return the secure URL."""
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        resource_type=resource_type,   # "image" or "video"
    )
    return result["secure_url"]
