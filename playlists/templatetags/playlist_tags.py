from django import template

from playlists.models import Playlist

register = template.Library()


@register.inclusion_tag("playlists/_add_to_playlist_form.html", takes_context=True)
def add_to_playlist_form(context, track):
    """Usage: {% add_to_playlist_form track %}
    Renders a dropdown of the current user's playlists (or a link to create
    one) that POSTs to the add_track view."""
    user = context["request"].user
    playlists = (
        Playlist.objects.filter(owner=user).order_by("name")
        if user.is_authenticated
        else Playlist.objects.none()
    )
    return {
        "track": track,
        "playlists": playlists,
        "user": user,
        # Inclusion tags render in a fresh context, so pass the CSRF token in
        # explicitly or {% csrf_token %} would be empty and the POST rejected.
        "csrf_token": context.get("csrf_token"),
    }