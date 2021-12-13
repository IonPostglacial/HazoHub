from django.contrib import admin
from .models import Book, Character, Dataset, ExtraField, FileSharing, Hierarchy, Icon, Item, ItemName, Language, State, Taxon, TaxonState


admin.site.register(Dataset)
admin.site.register(FileSharing)
admin.site.register(Language)
admin.site.register(Icon)
admin.site.register(ExtraField)
admin.site.register(Book)
admin.site.register(Item)
admin.site.register(ItemName)
admin.site.register(Character)
admin.site.register(Taxon)
admin.site.register(State)
admin.site.register(TaxonState)
admin.site.register(Hierarchy)