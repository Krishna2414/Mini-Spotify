import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from tracks.models import Track

from .forms import PlaylistForm
from .models import Playlist

MEDIA = tempfile.mkdtemp()


def fake_mp3(name="song.mp3"):
    return SimpleUploadedFile(name, b"ID3fakeaudio", content_type="audio/mpeg")


@override_settings(MEDIA_ROOT=MEDIA)
class PlaylistBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user("sam", password="pass12345!")
        self.other = User.objects.create_user("alex", password="pass12345!")
        self.track = Track.objects.create(
            title="Night Drive", artist="Synth Co", genre="electronic",
            audio=fake_mp3(), uploaded_by=self.user,
        )

    def login(self, username="sam"):
        self.client.login(username=username, password="pass12345!")


class PlaylistCreateListTests(PlaylistBase):
    def test_create_requires_login(self):
        response = self.client.get(reverse("playlist_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_list_requires_login(self):
        response = self.client.get(reverse("playlist_list"))
        self.assertEqual(response.status_code, 302)

    def test_create_shows_playlist_page_and_success_message(self):
        self.login()
        response = self.client.post(
            reverse("playlist_create"),
            {"name": "Chill", "description": "Relaxing"},
            follow=True,
        )
        playlist = Playlist.objects.get(name="Chill")
        self.assertEqual(playlist.owner, self.user)
        self.assertRedirects(response, reverse("playlist_detail", args=[playlist.pk]))
        self.assertContains(response, "created")

    def test_duplicate_name_rejected_ignoring_case(self):
        Playlist.objects.create(owner=self.user, name="Chill")
        form = PlaylistForm({"name": "cHiLL"}, owner=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_same_name_allowed_for_different_users(self):
        Playlist.objects.create(owner=self.other, name="Chill")
        self.assertTrue(PlaylistForm({"name": "Chill"}, owner=self.user).is_valid())

    def test_database_blocks_duplicates(self):
        Playlist.objects.create(owner=self.user, name="Chill")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Playlist.objects.create(owner=self.user, name="CHILL")

    def test_list_shows_only_my_playlists_with_track_counts(self):
        mine = Playlist.objects.create(owner=self.user, name="Mine")
        mine.tracks.add(self.track)
        Playlist.objects.create(owner=self.user, name="Empty")
        Playlist.objects.create(owner=self.other, name="Theirs")
        self.login()
        response = self.client.get(reverse("playlist_list"))
        self.assertContains(response, "Mine")
        self.assertContains(response, "1 track")
        self.assertContains(response, "0 tracks")
        self.assertNotContains(response, "Theirs")


class AddToPlaylistTests(PlaylistBase):
    def post_add(self, playlist_id, **kwargs):
        return self.client.post(
            reverse("add_track", args=[self.track.pk]), {"playlist": playlist_id}, **kwargs
        )

    # --- the dropdown on the track page ---
    def test_track_page_shows_dropdown_of_my_playlists(self):
        Playlist.objects.create(owner=self.user, name="Chill")
        Playlist.objects.create(owner=self.other, name="Not Mine")
        self.login()
        response = self.client.get(self.track.get_absolute_url())
        self.assertContains(response, "Add to playlist")
        self.assertContains(response, "Chill")
        self.assertNotContains(response, "Not Mine")

    def test_track_page_links_to_create_when_no_playlists(self):
        self.login()
        response = self.client.get(self.track.get_absolute_url())
        self.assertContains(response, reverse("playlist_create"))
        self.assertNotContains(response, "<select")

    # --- adding ---
    def test_add_track_to_my_playlist(self):
        playlist = Playlist.objects.create(owner=self.user, name="Chill")
        self.login()
        response = self.post_add(playlist.pk, follow=True)
        self.assertRedirects(response, self.track.get_absolute_url())
        self.assertIn(self.track, playlist.tracks.all())
        self.assertContains(response, "Added")

    def test_adding_same_track_twice_shows_already_in_playlist(self):
        playlist = Playlist.objects.create(owner=self.user, name="Chill")
        self.login()
        self.post_add(playlist.pk)
        response = self.post_add(playlist.pk, follow=True)
        self.assertContains(response, "already in this playlist")
        self.assertEqual(playlist.tracks.count(), 1)

    # --- blocked cases ---
    def test_cannot_add_to_someone_elses_playlist(self):
        theirs = Playlist.objects.create(owner=self.other, name="Theirs")
        self.login()  # logged in as sam
        response = self.post_add(theirs.pk)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(theirs.tracks.count(), 0)

    def test_add_track_is_post_only(self):
        self.login()
        response = self.client.get(reverse("add_track", args=[self.track.pk]))
        self.assertEqual(response.status_code, 405)

    def test_add_track_requires_login(self):
        playlist = Playlist.objects.create(owner=self.user, name="Chill")
        response = self.post_add(playlist.pk)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
        self.assertEqual(playlist.tracks.count(), 0)

    def test_blank_playlist_choice_shows_error(self):
        self.login()
        response = self.post_add("", follow=True)
        self.assertContains(response, "choose a playlist")

# remove track
class RemoveTrackTests(PlaylistBase):
    def test_remove_track_from_my_playlist(self):
        playlist = Playlist.objects.create(owner=self.user, name="Chill")
        playlist.tracks.add(self.track)
        self.login()
        response = self.client.post(
            reverse("remove_track", args=[playlist.pk, self.track.pk]), follow=True
        )
        self.assertRedirects(response, reverse("playlist_detail", args=[playlist.pk]))
        self.assertEqual(playlist.tracks.count(), 0)
        self.assertTrue(Track.objects.filter(pk=self.track.pk).exists())  # track survives

    def test_cannot_remove_from_someone_elses_playlist(self):
        theirs = Playlist.objects.create(owner=self.other, name="Theirs")
        theirs.tracks.add(self.track)
        self.login()  # logged in as sam
        response = self.client.post(reverse("remove_track", args=[theirs.pk, self.track.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(theirs.tracks.count(), 1)

    def test_remove_is_post_only(self):
        playlist = Playlist.objects.create(owner=self.user, name="Chill")
        self.login()
        response = self.client.get(reverse("remove_track", args=[playlist.pk, self.track.pk]))
        self.assertEqual(response.status_code, 405)


@override_settings(MEDIA_ROOT=MEDIA)
class SearchTests(TestCase):
    def setUp(self):
        user = User.objects.create_user("sam", password="pass12345!")
        for title, artist in [("Night Drive", "Synth Co"), ("Ocean Glow", "Calm Waves"),
                              ("Blue Hour", "Jazz Trio")]:
            Track.objects.create(title=title, artist=artist,
                                 audio=SimpleUploadedFile("a.mp3", b"ID3"), uploaded_by=user)

    def search(self, q):
        return self.client.get(reverse("search"), {"q": q})

    def test_search_by_title_ignores_case(self):
        response = self.search("night DRIVE")
        self.assertContains(response, "Night Drive")
        self.assertNotContains(response, "Ocean Glow")

    def test_search_by_artist(self):
        response = self.search("jazz")
        self.assertContains(response, "Blue Hour")
        self.assertNotContains(response, "Night Drive")

    def test_partial_match(self):
        self.assertContains(self.search("ocea"), "Ocean Glow")

    def test_results_are_playable_cards_with_count(self):
        response = self.search("o")  # matches all three
        self.assertContains(response, "3 results for")
        self.assertContains(response, "play-btn", count=3)

    def test_one_result_is_singular(self):
        self.assertContains(self.search("synth"), "1 result for")

    def test_no_matches_message(self):
        self.assertContains(self.search("zzzz"), "No tracks match your search.")

    def test_empty_search_shows_no_results(self):
        response = self.search("")
        self.assertNotContains(response, "play-btn")
        self.assertContains(response, "Type a song title")

    def test_navbar_search_box_points_to_search(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'action="{reverse("search")}"')
        self.assertContains(response, 'name="q"')


@override_settings(MEDIA_ROOT=MEDIA)
class PlaylistPrivacyTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pass12345!")
        self.other = User.objects.create_user("other", password="pass12345!")

    def test_new_playlists_are_private_by_default(self):
        self.client.login(username="owner", password="pass12345!")
        self.client.post(reverse("playlist_create"), {"name": "Chill"})
        self.assertFalse(Playlist.objects.get(name="Chill").is_public)

    def test_owner_can_make_playlist_public(self):
        self.client.login(username="owner", password="pass12345!")
        self.client.post(reverse("playlist_create"), {"name": "Party", "is_public": "on"})
        self.assertTrue(Playlist.objects.get(name="Party").is_public)

    def test_public_playlist_visible_to_logged_out_visitor(self):
        p = Playlist.objects.create(owner=self.owner, name="Party", is_public=True)
        response = self.client.get(p.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Party")

    def test_public_playlist_visible_to_other_user(self):
        p = Playlist.objects.create(owner=self.owner, name="Party", is_public=True)
        self.client.login(username="other", password="pass12345!")
        self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 200)

    def test_private_playlist_403_for_other_user(self):
        p = Playlist.objects.create(owner=self.owner, name="Secret")
        self.client.login(username="other", password="pass12345!")
        response = self.client.get(p.get_absolute_url())
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, "Secret", status_code=403)

    def test_private_playlist_403_for_logged_out_visitor(self):
        p = Playlist.objects.create(owner=self.owner, name="Secret")
        self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 403)

    def test_owner_can_view_private_playlist(self):
        p = Playlist.objects.create(owner=self.owner, name="Secret")
        self.client.login(username="owner", password="pass12345!")
        response = self.client.get(p.get_absolute_url())
        self.assertContains(response, "Private")

    def test_public_badge_in_list(self):
        Playlist.objects.create(owner=self.owner, name="Party", is_public=True)
        Playlist.objects.create(owner=self.owner, name="Secret")
        self.client.login(username="owner", password="pass12345!")
        response = self.client.get(reverse("playlist_list"))
        self.assertContains(response, "bi-globe", count=1)

    def test_visitor_cannot_edit_public_playlist(self):
        p = Playlist.objects.create(owner=self.owner, name="Party", is_public=True)
        self.client.login(username="other", password="pass12345!")
        response = self.client.get(reverse("playlist_update", args=[p.pk]))
        self.assertEqual(response.status_code, 404)

    def test_friendly_403_page(self):
        p = Playlist.objects.create(owner=self.owner, name="Secret")
        response = self.client.get(p.get_absolute_url())
        self.assertContains(response, "This is private", status_code=403)
