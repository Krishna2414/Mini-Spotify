from django.conf import settings
from django.db import models
from django.urls import reverse

from tracks.models import Track


class Playlist(models.Model):
    # ---- Fields (database columns) ----
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playlists"
    )
    tracks = models.ManyToManyField(Track, blank=True, related_name="playlists")
    is_public = models.BooleanField(                                    # ← US25
        default=False, help_text="Public playlists can be viewed by anyone."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="unique_playlist_name_per_user")
        ]

    # ---- Methods ----
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("playlist_detail", args=[self.pk])

    def can_view(self, user):                                           # ← US25
        """Anyone can see a public playlist; only the owner can see a private one."""
        return self.is_public or self.owner == user
