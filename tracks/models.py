from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse

from .storage import audio_storage
from .validators import validate_audio_size


class Track(models.Model):
    GENRES = [
        ("pop", "Pop"), ("rock", "Rock"), ("hiphop", "Hip-hop"),
        ("electronic", "Electronic"), ("jazz", "Jazz"), ("classical", "Classical"),
        ("lofi", "Lo-fi"), ("other", "Other"),
    ]

    title = models.CharField(max_length=120)
    artist = models.CharField(max_length=120)
    genre = models.CharField(max_length=20, choices=GENRES, default="other")
    cover = models.ImageField(upload_to="covers/", blank=True)
    audio = models.FileField(
        upload_to="tracks/",
        storage=audio_storage,
        validators=[
            FileExtensionValidator(["mp3", "wav", "ogg", "m4a"]),
            validate_audio_size,
        ],
        help_text="MP3, WAV, OGG or M4A, max 10 MB. Royalty-free music only.",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tracks"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} – {self.artist}"

    def get_absolute_url(self):
        return reverse("track_detail", args=[self.pk])
