from datetime import datetime
from pathlib import Path
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import Group
from django.conf import settings


def _item_owner_as_of(cls, datetime: datetime):
    return cls.objects.select_related('item').select_related('item__creation_version').filter(
            Q(item__creation_version__date__lte=datetime),
            Q(item__deletion_version__isnull=True) | Q(item__deletion_version__gte=datetime))

def _item_owner_from_dataset_version(cls, version: 'DatasetVersion'):
    return cls.objects.select_related('item').select_related('item__creation_version').filter(
        Q(item__deletion_version__isnull=True) | Q(item__deletion_version__number__gt=version.number),
        item__creation_version__dataset=version.dataset,
        item__creation_version__number__lte=version.number)


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

class DatasetVersion(models.Model):
    class Meta:
        unique_together = (('dataset', 'number'),)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    number = models.IntegerField()
    created_on = models.DateTimeField()

    @classmethod
    def last_for_dataset(cls, ds: Dataset):
        return cls.objects.filter(dataset=ds).order_by('-number').first()

    def __str__(self):
        return f'{self.dataset} #{self.number} ({self.created_on.isoformat()})'

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
        unique_together = (('ref', 'creation_version'),)
    ref = models.CharField(max_length=8)
    creation_version = models.ForeignKey(DatasetVersion, on_delete=models.CASCADE, related_name='created_items', null=True)
    deletion_version = models.ForeignKey(DatasetVersion, on_delete=models.CASCADE, null=True, blank=True, related_name='deleted_items')
    name = models.CharField(max_length=256)

    def __str__(self):
        return f"{self.name} (v{self.creation_version.number})"

class ItemPicture(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="pictures")
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

    as_of = classmethod(_item_owner_as_of)
    from_dataset_version = classmethod(_item_owner_from_dataset_version)

    def __str__(self):
        return str(self.item)

class State(models.Model):
    item = models.OneToOneField(Item, on_delete=models.CASCADE, primary_key=True)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    color = models.CharField(max_length=8)

    as_of = classmethod(_item_owner_as_of)
    from_dataset_version = classmethod(_item_owner_from_dataset_version)

    def __str__(self):
        return str(self.item)

class CharacterRequiredState(models.Model):
    class Meta:
        unique_together = (('character', 'state'),)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)

class CharacterInherentState(models.Model):
    character = models.OneToOneField(Character, on_delete=models.CASCADE, primary_key=True, related_name="inherent_state")
    state = models.OneToOneField(State, on_delete=models.CASCADE, related_name="inherent_character")

class Taxon(models.Model):
    item = models.OneToOneField(Item, on_delete=models.CASCADE, primary_key=True)
    author = models.CharField(max_length=256)
    description = models.TextField(null=True, blank=True)
    website = models.CharField(max_length=512, null=True, blank=True)

    as_of = classmethod(_item_owner_as_of)
    from_dataset_version = classmethod(_item_owner_from_dataset_version)

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

    @classmethod
    def from_dataset_version(cls, version: DatasetVersion):
        return cls.objects.select_related('taxon', 'taxon__item').filter(
            Q(state__item__deletion_version__isnull=True) | Q(state__item__deletion_version__number__gt=version.number),
            state__item__creation_version__dataset=version.dataset,
            state__item__creation_version__number__lte=version.number)

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
    entry = models.ForeignKey(DictionaryEntry, on_delete=models.CASCADE, related_name='translations')
    lang = models.ForeignKey(Language, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)
    definition = models.TextField()