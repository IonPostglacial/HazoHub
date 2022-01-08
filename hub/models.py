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

class Dataset(models.Model):
    src = models.FilePathField(null=True, blank=True)
    name = models.CharField(max_length=256)

    def __str__(self):
        return self.name

class Icon(models.Model):
    path = models.FilePathField()

class ExtraField(models.Model):
    ref = models.CharField(max_length=8, unique=True)
    std = models.BooleanField()
    label = models.CharField(max_length=256)
    icon = models.ForeignKey(Icon, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.label

class Book(models.Model):
    ref = models.CharField(max_length=8, unique=True)
    label = models.CharField(max_length=256)

    def __str__(self):
        return self.label

class Item(models.Model):
    class Meta:
        unique_together = (('ref', 'dataset'),)
    ref = models.CharField(max_length=8)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)

    def __str__(self):
        return self.name

class ItemPicture(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    url = models.CharField(max_length=512)
    label = models.CharField(max_length=256)
    photo = models.ImageField(upload_to='static/img', null=True, blank=True)

    def __str__(self):
        return f'{self.item}'

class Language(models.Model):
    code = models.CharField(max_length=2, primary_key=True)
    label = models.CharField(max_length=256)

    def __str__(self):
        return f'{self.label} ({self.code})'

class ItemName(models.Model):
    class Meta:
        unique_together = (('item', 'lang'),)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    lang = models.ForeignKey(Language, on_delete=models.CASCADE)
    text = models.CharField(max_length=256)

    def __str__(self):
        return f'{self.item.name} [{self.lang.code}]'

class Hierarchy(models.Model):
    class Meta:
        unique_together = (('ancestor', 'descendant'),)
    ancestor = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='descendants')
    descendant = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='ancestors')
    length = models.IntegerField(default=0)

    def __str__(self):
        if self.ancestor_id == self.descendant_id:
            return f'"{self.ancestor.name}" to itself'
        return f'"{self.ancestor.name}" to "{self.descendant.name}" ({self.length})'

class Character(models.Model):
    item = models.OneToOneField(Item, on_delete=models.CASCADE, primary_key=True)

    def __str__(self):
        return str(self.item)

class State(models.Model):
    item = models.OneToOneField(Item, on_delete=models.CASCADE, primary_key=True)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    color = models.CharField(max_length=8)

    def __str__(self):
        return str(self.item)

class CharacterRequiredState(models.Model):
    class Meta:
        unique_together = (('character', 'state'),)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)

class Taxon(models.Model):
    item = models.OneToOneField(Item, on_delete=models.CASCADE, primary_key=True)
    author = models.CharField(max_length=256)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        if self.author:
            return f'{self.item} - {self.author}'
        return str(self.item)

class ExtraFieldValue(models.Model):
    class Meta:
        unique_together = (('taxon', 'field'),)
    taxon = models.ForeignKey(Taxon, on_delete=models.CASCADE)
    field = models.ForeignKey(ExtraField, on_delete=models.CASCADE)
    value = models.CharField(max_length=256)

class BookInfo(models.Model):
    class Meta:
        unique_together = (('taxon', 'book'),)
    taxon = models.ForeignKey(Taxon, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    fasc = models.CharField(max_length=256)
    page = models.IntegerField()
    text = models.TextField()

class TaxonState(models.Model):
    class Meta:
        unique_together = (('taxon', 'state'),)
    taxon = models.ForeignKey(Taxon, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.taxon} > {self.state}'

class DictionaryVersion(models.Model):
    number = models.PositiveIntegerField(primary_key=True)
    created_on = models.DateTimeField()

class DictionaryOrgan(models.Model):
    name = models.CharField(max_length=256)

    def __str__(self):
        return f'{self.name}'

class DictionaryEntry(models.Model):
    creation_version = models.ForeignKey(DictionaryVersion, on_delete=models.SET_NULL, null=True, related_name='created_entries')
    deletion_version = models.ForeignKey(DictionaryVersion, on_delete=models.CASCADE, null=True, blank=True, related_name='deleted_entries')
    url = models.CharField(max_length=512, default="")
    number = models.PositiveIntegerField(null=True, blank=True)
    organ = models.ForeignKey(DictionaryOrgan, null=True, blank=True, on_delete=models.SET_NULL)

class DictionaryEntryByLang(models.Model):
    class Meta:
        unique_together = (('entry', 'lang'),)
    entry = models.ForeignKey(DictionaryEntry, on_delete=models.CASCADE)
    lang = models.ForeignKey(Language, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)
    definition = models.TextField()