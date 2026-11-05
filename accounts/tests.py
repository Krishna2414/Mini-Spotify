from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AccountTests(TestCase):
    def test_profile_created_with_user(self):
        user = User.objects.create_user("sam", password="pass12345!")
        self.assertTrue(hasattr(user, "profile"))
        self.assertFalse(user.profile.is_premium)

    def test_signup_logs_user_in(self):
        response = self.client.post(reverse("signup"), {
            "username": "newuser", "email": "n@example.com",
            "password1": "Str0ngPass!word", "password2": "Str0ngPass!word",
        })
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_profile_edit_requires_login(self):
        response = self.client.get(reverse("profile_edit"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_user_can_edit_bio(self):
        User.objects.create_user("sam", password="pass12345!")
        self.client.login(username="sam", password="pass12345!")
        self.client.post(reverse("profile_edit"), {"bio": "I love jazz"})
        self.assertEqual(User.objects.get(username="sam").profile.bio, "I love jazz")

    def test_delete_account(self):
        User.objects.create_user("sam", password="pass12345!")
        self.client.login(username="sam", password="pass12345!")
        self.client.post(reverse("account_delete"))
        self.assertFalse(User.objects.filter(username="sam").exists())
