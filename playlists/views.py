from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from tracks.models import Track
from django.core.exceptions import PermissionDenied
from django.conf import settings

from .forms import PlaylistForm
from .models import Playlist


@login_required
def playlist_create(request):
    if not can_create_playlist(request.user):
        messages.warning(
            request,
            f"Free accounts can have {settings.FREE_PLAYLIST_LIMIT} playlists. Upgrade to Premium for unlimited.",
        )
        return redirect("playlist_list")
    if request.method == "POST":
        form = PlaylistForm(request.POST, owner=request.user)
        if form.is_valid():
            playlist = form.save(commit=False)  # build the object but don't save yet
            playlist.owner = request.user       # attach the owner first
            try:
                playlist.save()
            except IntegrityError:
                # Safety net if two identical requests arrive at the same moment.
                form.add_error("name", "You already have a playlist with this name.")
            else:
                messages.success(request, f'Playlist "{playlist.name}" created.')
                return redirect("playlist_detail", pk=playlist.pk)
    else:
        form = PlaylistForm(owner=request.user)
    return render(request, "playlists/playlist_form.html", {"form": form})


def can_create_playlist(user):
    """Premium users have no limit; free users get FREE_PLAYLIST_LIMIT playlists."""
    if user.profile.is_premium:
        return True
    return user.playlists.count() < settings.FREE_PLAYLIST_LIMIT


@login_required
def playlist_list(request):
    playlists = request.user.playlists.annotate(track_count=Count("tracks"))
    return render(request, "playlists/playlist_list.html", {
        "playlists": playlists,
        "used": playlists.count(),
        "limit": settings.FREE_PLAYLIST_LIMIT,
        "can_create": can_create_playlist(request.user),
    })


def playlist_detail(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk)
    if not playlist.can_view(request.user):
        raise PermissionDenied
    return render(request, "playlists/playlist_detail.html", {"playlist": playlist})


@login_required
@require_POST  # GET requests get a 405; this view only changes data
def add_track(request, track_pk):
    track = get_object_or_404(Track, pk=track_pk)

    playlist_id = request.POST.get("playlist", "")
    if not playlist_id.isdecimal():  # blank / junk value from the dropdown
        messages.error(request, "Please choose a playlist.")
        return redirect(track)

    # owner=request.user is the security check: someone else's playlist
    # simply "doesn't exist" for you, so you get a 404 and nothing is added.
    playlist = get_object_or_404(Playlist, pk=playlist_id, owner=request.user)

    if playlist.tracks.filter(pk=track.pk).exists():
        messages.warning(request, f'"{track.title}" is already in this playlist.')
    else:
        playlist.tracks.add(track)
        messages.success(request, f'Added "{track.title}" to "{playlist.name}".')
    return redirect(track)  # back to the track page (uses Track.get_absolute_url)

# Create your views here.
@login_required
@require_POST
def remove_track(request, pk, track_pk):
    # owner=request.user: you can only change your own playlists (404 otherwise)
    playlist = get_object_or_404(Playlist, pk=pk, owner=request.user)
    track = get_object_or_404(Track, pk=track_pk)
    if playlist.tracks.filter(pk=track.pk).exists():
        playlist.tracks.remove(track)  # unlinks only; the Track row is not deleted
        messages.success(request, f'Removed "{track.title}" from "{playlist.name}".')
    else:
        messages.warning(request, f'"{track.title}" is not in this playlist.')
    return redirect("playlist_detail", pk=playlist.pk)


def search(request):
    """Search tracks by title or artist (case-insensitive)."""
    query = request.GET.get("q", "").strip()
    tracks = Track.objects.none()
    if query:
        tracks = Track.objects.filter(
            Q(title__icontains=query) | Q(artist__icontains=query)
        )
    return render(request, "playlists/search.html", {
        "query": query,
        "tracks": tracks,
        "count": tracks.count(),
    })
