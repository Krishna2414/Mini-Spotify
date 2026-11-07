from django.core.exceptions import ValidationError

MAX_AUDIO_MB = 10


def validate_audio_size(file):
    if file.size > MAX_AUDIO_MB * 1024 * 1024:
        raise ValidationError(f"Audio files must be under {MAX_AUDIO_MB} MB.")
