import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

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
