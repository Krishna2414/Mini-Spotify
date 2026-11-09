import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.dateformat import format as date_format
from django.utils.timezone import localtime

from .models import Track

MEDIA = tempfile.mkdtemp()


def fake_mp3(name="song.mp3", size=None):
    content = b"ID3" + (b"0" * size if size else b"fakeaudio")
    return SimpleUploadedFile(name, content, content_type="audio/mpeg")


@override_settings(MEDIA_ROOT=MEDIA)
class TrackUploadTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user("sam", password="pass12345!")

    def test_upload_page_requires_login(self):
        response = self.client.get(reverse("track_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_logged_in_user_can_upload(self):
        self.client.login(username="sam", password="pass12345!")
        response = self.client.post(reverse("track_create"), {
            "title": "Night Drive", "artist": "Synth Co", "genre": "electronic",
            "audio": fake_mp3("night.mp3"),
        }, follow=True)
        track = Track.objects.get(title="Night Drive")
        self.assertRedirects(response, track.get_absolute_url())
        self.assertEqual(track.uploaded_by, self.user)
        self.assertContains(response, "Track uploaded.")

    def test_cover_is_optional_and_placeholder_shows(self):
        self.client.login(username="sam", password="pass12345!")
        response = self.client.post(reverse("track_create"), {
            "title": "No Cover", "artist": "X", "genre": "other", "audio": fake_mp3(),
        }, follow=True)
        self.assertContains(response, "track-cover-placeholder")

    def test_rejects_wrong_file_type(self):
        self.client.login(username="sam", password="pass12345!")
        response = self.client.post(reverse("track_create"), {
            "title": "Bad", "artist": "X", "genre": "other",
            "audio": SimpleUploadedFile("virus.exe", b"x"),
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Track.objects.filter(title="Bad").exists())

    def test_rejects_file_over_10mb(self):
        self.client.login(username="sam", password="pass12345!")
        response = self.client.post(reverse("track_create"), {
            "title": "Huge", "artist": "X", "genre": "other",
            "audio": fake_mp3("huge.mp3", size=11 * 1024 * 1024),
        })
        self.assertContains(response, "under 10 MB")
        self.assertFalse(Track.objects.filter(title="Huge").exists())


@override_settings(MEDIA_ROOT=MEDIA)
class TrackLibraryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("sam", password="pass12345!")

    def make_track(self, title):
        return Track.objects.create(
            title=title, artist="Test Artist", genre="lofi",
            audio=fake_mp3(), uploaded_by=self.user,
        )

    def test_empty_library_shows_friendly_message(self):
        response = self.client.get(reverse("track_list"))
        self.assertContains(response, "No tracks yet")

    def test_library_shows_card_with_play_button(self):
        track = self.make_track("Sunrise Walk")
        response = self.client.get(reverse("track_list"))
        self.assertContains(response, "Sunrise Walk")
        self.assertContains(response, "Test Artist")
        self.assertContains(response, "play-btn")
        self.assertContains(response, f'data-src="{track.audio.url}"')

    def test_newest_tracks_first(self):
        self.make_track("Old Song")
        self.make_track("New Song")
        tracks = list(self.client.get(reverse("track_list")).context["tracks"])
        self.assertEqual(tracks[0].title, "New Song")

    def test_more_than_12_tracks_are_paginated(self):
        for i in range(13):
            self.make_track(f"Song {i}")
        response = self.client.get(reverse("track_list"))
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["tracks"]), 12)
        page2 = self.client.get(reverse("track_list") + "?page=2")
        self.assertEqual(len(page2.context["tracks"]), 1)


@override_settings(MEDIA_ROOT=MEDIA)
class TrackEditTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pass12345!")
        self.other = User.objects.create_user("other", password="pass12345!")
        self.track = Track.objects.create(
            title="Sunrse Walk", artist="Lo-fi Lab", genre="lofi",
            audio=fake_mp3(), uploaded_by=self.owner,
        )
        self.edit_url = reverse("track_update", args=[self.track.pk])

    def test_edit_button_only_shown_to_owner(self):
        self.client.login(username="owner", password="pass12345!")
        self.assertContains(self.client.get(self.track.get_absolute_url()), self.edit_url)
        self.client.login(username="other", password="pass12345!")
        self.assertNotContains(self.client.get(self.track.get_absolute_url()), self.edit_url)

    def test_non_owner_gets_403(self):
        self.client.login(username="other", password="pass12345!")
        self.assertEqual(self.client.get(self.edit_url).status_code, 403)
        response = self.client.post(self.edit_url, {"title": "Hacked", "artist": "X", "genre": "other"})
        self.assertEqual(response.status_code, 403)
        self.track.refresh_from_db()
        self.assertEqual(self.track.title, "Sunrse Walk")

    def test_logged_out_user_sent_to_login(self):
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_owner_can_edit_and_sees_success_message(self):
        self.client.login(username="owner", password="pass12345!")
        response = self.client.post(self.edit_url, {
            "title": "Sunrise Walk", "artist": "Lo-fi Lab", "genre": "lofi",
        }, follow=True)
        self.track.refresh_from_db()
        self.assertEqual(self.track.title, "Sunrise Walk")
        self.assertRedirects(response, self.track.get_absolute_url())
        self.assertContains(response, "Track updated.")


@override_settings(MEDIA_ROOT=MEDIA)
class TrackDetailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("sam", password="pass12345!")
        self.track = Track.objects.create(
            title="Night Drive", artist="Synth Co", genre="electronic",
            audio=fake_mp3(), uploaded_by=self.user,
        )

    def test_page_shows_track_details(self):
        response = self.client.get(self.track.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Night Drive")
        self.assertContains(response, "Synth Co")
        self.assertContains(response, "Electronic")  # genre display name
        self.assertContains(response, date_format(localtime(self.track.created_at), "j M Y"))
        self.assertContains(response, "track-cover-placeholder")  # no cover uploaded

    def test_play_button_has_player_data(self):
        response = self.client.get(self.track.get_absolute_url())
        self.assertContains(response, "btn-lg play-btn")
        self.assertContains(response, f'data-src="{self.track.audio.url}"')
        self.assertContains(response, 'data-title="Night Drive"')

    def test_uploader_links_to_profile(self):
        response = self.client.get(self.track.get_absolute_url())
        self.assertContains(response, f'href="{reverse("profile_detail", args=["sam"])}"')

    def test_visitors_can_view_without_logging_in(self):
        self.assertEqual(self.client.get(self.track.get_absolute_url()).status_code, 200)

    def test_missing_track_returns_404(self):
        self.assertEqual(self.client.get(reverse("track_detail", args=[999])).status_code, 404)


@override_settings(MEDIA_ROOT=MEDIA)
class TrackDeleteTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pass12345!")
        self.other = User.objects.create_user("other", password="pass12345!")
        self.track = Track.objects.create(
            title="Blue Hour", artist="Jazz Trio", genre="jazz",
            audio=fake_mp3(), uploaded_by=self.owner,
        )
        self.delete_url = reverse("track_delete", args=[self.track.pk])

    def test_get_shows_confirmation_and_deletes_nothing(self):
        self.client.login(username="owner", password="pass12345!")
        response = self.client.get(self.delete_url)
        self.assertContains(response, 'Delete "Blue Hour"?')
        self.assertTrue(Track.objects.filter(pk=self.track.pk).exists())

    def test_delete_button_only_shown_to_owner(self):
        self.client.login(username="owner", password="pass12345!")
        self.assertContains(self.client.get(self.track.get_absolute_url()), self.delete_url)
        self.client.login(username="other", password="pass12345!")
        self.assertNotContains(self.client.get(self.track.get_absolute_url()), self.delete_url)

    def test_non_owner_cannot_delete(self):
        self.client.login(username="other", password="pass12345!")
        self.assertEqual(self.client.get(self.delete_url).status_code, 403)
        self.assertEqual(self.client.post(self.delete_url).status_code, 403)
        self.assertTrue(Track.objects.filter(pk=self.track.pk).exists())

    def test_owner_can_delete(self):
        self.client.login(username="owner", password="pass12345!")
        response = self.client.post(self.delete_url, follow=True)
        self.assertRedirects(response, reverse("track_list"))
        self.assertContains(response, "was deleted")
        self.assertFalse(Track.objects.filter(pk=self.track.pk).exists())

    def test_audio_file_removed_from_storage(self):
        storage, name = self.track.audio.storage, self.track.audio.name
        self.assertTrue(storage.exists(name))
        self.client.login(username="owner", password="pass12345!")
        self.client.post(self.delete_url)
        self.assertFalse(storage.exists(name))


@override_settings(MEDIA_ROOT=MEDIA)
class ProfileUploadsTests(TestCase):
    def setUp(self):
        self.sam = User.objects.create_user("sam", password="pass12345!")
        self.alex = User.objects.create_user("alex", password="pass12345!")

    def test_profile_lists_users_uploads_as_cards(self):
        Track.objects.create(title="Ocean Glow", artist="Calm Waves",
                             audio=fake_mp3(), uploaded_by=self.sam)
        Track.objects.create(title="Someone Else's Song", artist="X",
                             audio=fake_mp3(), uploaded_by=self.alex)
        response = self.client.get(reverse("profile_detail", args=["sam"]))
        self.assertContains(response, "Ocean Glow")
        self.assertContains(response, "data-track-card")
        self.assertContains(response, "play-btn")
        self.assertNotContains(response, "Someone Else&#x27;s Song")
        self.assertNotContains(response, "No uploads yet.")

    def test_user_with_no_uploads_shows_message(self):
        response = self.client.get(reverse("profile_detail", args=["alex"]))
        self.assertContains(response, "No uploads yet.")


@override_settings(MEDIA_ROOT=MEDIA)
class PlayerBarTests(TestCase):
    """The JavaScript itself is tested by hand (see TESTING.md); these check the HTML it needs."""

    def setUp(self):
        user = User.objects.create_user("sam", password="pass12345!")
        Track.objects.create(title="Ocean Glow", artist="Calm Waves",
                             audio=fake_mp3(), uploaded_by=user)

    def test_player_bar_and_script_on_every_page(self):
        for url in [reverse("home"), reverse("track_list")]:
            response = self.client.get(url)
            self.assertContains(response, 'id="player"')
            self.assertContains(response, '<audio id="audio"')
            self.assertContains(response, "js/player.js")

    def test_player_starts_hidden(self):
        response = self.client.get(reverse("track_list"))
        self.assertContains(response, 'aria-label="Music player" hidden')

    def test_volume_slider_present(self):
        response = self.client.get(reverse("track_list"))
        self.assertContains(response, 'id="volume" type="range"')
        self.assertContains(response, '<label for="volume" class="visually-hidden">Volume</label>')
