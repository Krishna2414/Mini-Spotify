from django import forms

from .models import Track


class TrackForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = ("title", "artist", "genre", "cover", "audio")
        widgets = {"audio": forms.ClearableFileInput(attrs={"accept": "audio/*"})}
