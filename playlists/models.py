from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class Playlist(models.Model):
    # Owner of the playlist. Deleting the user deletes their playlists.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="playlists",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Many-to-many with Dev 2's Track model. Deleting a track removes it
    # from every playlist automatically (track_confirm_delete.html promises this).
    tracks = models.ManyToManyField("tracks.Track", blank=True, related_name="playlists")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Database-level rule: one user can't have two playlists with the same
            # name, ignoring case ("Chill" == "chill"). Needs Django 4.0+ (you have 4.2).
            models.UniqueConstraint(
                Lower("name"), "owner", name="unique_playlist_name_per_owner_ci"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.owner})"

# Create your models here.
