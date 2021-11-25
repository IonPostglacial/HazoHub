from pathlib import Path
from django.db import models
from django.contrib.auth.models import Group
from django.conf import settings


class FileSharing(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    shared_with = models.ForeignKey(Group, null=True, blank=True, on_delete=models.SET_NULL)
    share_link = models.CharField(max_length=48)
    file_path = models.CharField(max_length=512)

    def __str__(self):
        return Path(self.file_path).name