from django import forms

from .models import Playlist


class PlaylistForm(forms.ModelForm):
    class Meta:
        model = Playlist
        fields = ("name", "description")  # owner is set in the view, never by the user
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, owner=None, **kwargs):
        # The view passes request.user so we know whose playlists to check.
        super().__init__(*args, **kwargs)
        self.owner = owner

    def clean_name(self):
        # Runs during is_valid(). Rejects a name this user already has, ignoring case.
        name = self.cleaned_data["name"].strip()
        duplicates = Playlist.objects.filter(owner=self.owner, name__iexact=name)
        if self.instance.pk:  # so a future "edit" form can keep its own name
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("You already have a playlist with this name.")
        return name