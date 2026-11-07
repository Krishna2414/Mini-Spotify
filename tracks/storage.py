"""Audio files need Cloudinary's 'video' resource type; locally we use the disk."""
from django.conf import settings
from django.core.files.storage import default_storage


def audio_storage():
    if settings.USE_CLOUDINARY:
        from cloudinary_storage.storage import VideoMediaCloudinaryStorage
        return VideoMediaCloudinaryStorage()
    return default_storage
