"""Audio files use Cloudinary only when explicitly enabled; otherwise they stay on disk."""
from django.conf import settings
from django.core.files.storage import default_storage


def audio_storage():
    if settings.USE_CLOUDINARY:
        try:
            from cloudinary_storage.storage import VideoMediaCloudinaryStorage
            return VideoMediaCloudinaryStorage()
        except Exception:
            pass
    return default_storage
