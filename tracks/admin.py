from django.contrib import admin

from .models import Track


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "genre", "uploaded_by", "created_at")
    list_filter = ("genre",)
    search_fields = ("title", "artist")
