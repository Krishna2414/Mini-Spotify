from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Track


@receiver(post_delete, sender=Track)
def delete_track_files(sender, instance, **kwargs):
    """Remove the audio and cover from storage (Cloudinary on the live site)
    so a deleted track can no longer be played from its old link."""
    if instance.audio:
        instance.audio.delete(save=False)
    if instance.cover:
        instance.cover.delete(save=False)
