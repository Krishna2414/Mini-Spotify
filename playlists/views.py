from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from tracks.models import Track

from .forms import PlaylistForm
from .models import Playlist


@login_required  # anonymous users are sent to LOGIN_URL ("login")
def playlist_create(request):
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


@login_required
def playlist_list(request):
    # Only my playlists, each annotated with how many tracks it holds.
    playlists = Playlist.objects.filter(owner=request.user).annotate(
        track_count=Count("tracks")
    )
    return render(request, "playlists/playlist_list.html", {"playlists": playlists})


@login_required
def playlist_detail(request, pk):
    # The page you land on after creating a playlist. Owner only (404 otherwise).
    playlist = get_object_or_404(Playlist, pk=pk, owner=request.user)
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