import datetime
import io
import json
import pathlib
import dataclasses
from typing import Optional

from typing import Dict
from hub.models import Character, CharacterInherentState, Dataset, DatasetVersion, Book, ExtraField, Hierarchy, Item, ItemName, ItemPicture, State, Taxon, TaxonState


@dataclasses.dataclass
class ItemInfo:
    id: int
    type: str
    parent_ref: str
    names: dict
    website: str = ""
    author: str = ""
    detail: str = ""
    states_refs: list = None
    inherent_state: Optional[None] = None
    pics: list = ""


@dataclasses.dataclass
class Picture:
    ref: str
    url: str
    label: str


def photo_to_picture(photo: dict) -> Picture:
    url = photo['url']
    label = photo['label']
    while isinstance(url, list) and len(url) > 0:
        url = url[0]
    while isinstance(label, list) and len(label) > 0:
        label = label[0]
    return Picture(ref=photo['id'], url=url, label=label)


def _import_dataset(src: pathlib.Path, input: io.TextIOBase):
    hazo_ds = json.load(input)
    ds = Dataset(src=src, name=hazo_ds['id'])
    last_version = DatasetVersion.last_for_dataset(ds)
    reimport = last_version is not None
    if reimport:
        version = DatasetVersion(dataset=ds, number=last_version.number + 1, created_on=datetime.datetime.now())
    else:
        ds.save()
        version = DatasetVersion(dataset=ds, number=1, created_on=datetime.datetime.now())
    version.save()

    for hazo_book in hazo_ds['books']:
        Book.objects.update_or_create(
            ref=hazo_book['id'], label=hazo_book['label'])
    for hazo_field in hazo_ds['extraFields']:
        ExtraField.objects.update_or_create(
            ref=hazo_field['id'], std=hazo_field['std'], label=hazo_field['label'], icon=None)
    items = []
    hierarchical_item = []
    items_info_by_ref: Dict[str, ItemInfo] = {}
    for state in hazo_ds['states']:
        state_item = Item(creation_version=version, ref=state['id'], name=state.get(
            'name') or state.get('nameEN') or state.get('nameCN') or "")
        items_info_by_ref[state_item.ref] = ItemInfo(
            id=None,
            type='state',
            parent_ref=state.get('parentId'),
            names={
                'FR': state.get('name') or "",
                'EN': state.get('nameEN') or "",
                'CN': state.get('nameCN') or "",
            },
            pics=map(photo_to_picture, state['photos']),
        )
        items.append(state_item)
    for hazo_ch in hazo_ds['characters']:
        item = Item(creation_version=version, ref=hazo_ch['id'], name=hazo_ch['name'])
        items_info_by_ref[item.ref] = ItemInfo(
            id=None,
            type='character',
            parent_ref=hazo_ch.get('parentId'),
            names={
                'EN': hazo_ch['nameEN'],
                'CN': hazo_ch['nameCN'],
            },
            states_refs=hazo_ch['states'],
            pics=map(photo_to_picture, hazo_ch['photos']),
            inherent_state=hazo_ch.get('inherent_state')
        )
        items.append(item)
        hierarchical_item.append(item)
    for hazo_taxon in hazo_ds['taxons']:
        item = Item(creation_version=version, ref=hazo_taxon['id'], name=hazo_taxon['name'])
        states_refs = []
        for description in hazo_taxon['descriptions']:
            states_refs += description['statesIds']
        items_info_by_ref[item.ref] = ItemInfo(
            id=None,
            type='taxon',
            parent_ref=hazo_taxon.get('parentId'),
            names={
                'EN': hazo_taxon['nameEN'],
                'V': hazo_taxon['vernacularName'],
                'CN': hazo_taxon['nameCN'],
            },
            website=hazo_taxon['website'],
            states_refs=states_refs,
            author=hazo_taxon['author'],
            detail=hazo_taxon['detail'],
            pics=map(photo_to_picture, hazo_taxon['photos']),
        )
        items.append(item)
        hierarchical_item.append(item)
    # TODO: Detect unchanged items to avoid creating a new version on each import
    Item.objects.filter(creation_version__dataset=ds).update(deletion_version=version)
    Item.objects.bulk_create(items)
    characters = []
    taxons = []
    states_by_id = {}
    names = []
    pics = []
    hierarchies = []
    taxon_states = []
    inherent_states = []

    for item in Item.objects.filter(creation_version__id=version.id):
        info = items_info_by_ref.get(item.ref)
        if info is None:
            continue
        info.id = item.id
        for lang_code, value in info.names.items():
            item_name = ItemName(item=item, text=value)
            item_name.lang_id = lang_code
            names.append(item_name)
        for pic in info.pics:
            pics.append(ItemPicture(item=item, url=pic.url, label=pic.label))

    for h_item in hierarchical_item:
        item_info = items_info_by_ref[h_item.ref]
        length = 0
        item_id = item_info.id
        item = Item(id=item_id)
        hierarchies.append(
            Hierarchy(ancestor=item, descendant=item, length=length))
        while item_info.parent_ref is not None:
            length += 1
            item_info = items_info_by_ref[item_info.parent_ref]
            parent = Item(id=item_info.id)
            hierarchies.append(
                Hierarchy(ancestor=parent, descendant=item, length=length))

    for info in items_info_by_ref.values():
        if info.type == 'character':
            character = Character()
            character.item_id = info.id
            characters.append(character)
            for state_ref in info.states_refs:
                state_info = items_info_by_ref[state_ref]
                state = State()
                state.item_id = state_info.id
                state.character_id = info.id
                states_by_id[state_info.id] = state
            if info.inherent_state is not None:
                inherent_states.append(CharacterInherentState(character=character, state=states_by_id[info.inherent_state]))
        elif info.type == 'taxon':
            taxon = Taxon(author=info.author,
                          description=info.detail, website=info.website)
            taxon.item_id = info.id
            taxons.append(taxon)
            for state_ref in info.states_refs:
                ts = TaxonState()
                ts.taxon_id = info.id
                ts.state_id = items_info_by_ref[state_ref].id
                taxon_states.append(ts)

    Hierarchy.objects.bulk_create(hierarchies)
    ItemName.objects.bulk_create(names)
    ItemPicture.objects.bulk_create(pics)
    Character.objects.bulk_create(characters)
    Taxon.objects.bulk_create(taxons)
    State.objects.bulk_create(states_by_id.values())
    CharacterInherentState.objects.bulk_create(inherent_states)
    TaxonState.objects.bulk_create(taxon_states)

def import_hazo(src: pathlib.Path):
    with src.open("r") as input:
        _import_dataset(src, input)
