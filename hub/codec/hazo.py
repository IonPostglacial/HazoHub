import io
import json
from os import stat
import pathlib
import dataclasses

from hub.models import Dataset, Book, ExtraField, Hierarchy, Item, Character, ItemName, Language, State, Taxon, TaxonState


@dataclasses.dataclass
class ItemInfo:
    id: int
    type: str
    parent_ref: str
    names: dict
    author: str = ""
    detail: str = ""
    states_refs: list = None

def _import_dataset(src: pathlib.Path, input: io.TextIOBase):
    hazo_ds = json.load(input)
    ds = Dataset(src=src, name=hazo_ds['id'])
    ds.save()

    for hazo_book in hazo_ds['books']:
        Book.objects.update_or_create(ref=hazo_book['id'], label=hazo_book['label'])
    for hazo_field in hazo_ds['extraFields']:
        ExtraField.objects.update_or_create(ref=hazo_field['id'], std=hazo_field['std'], label=hazo_field['label'], icon=None)
    items = []
    hierarchical_item = []
    items_info_by_ref = {}
    for state in hazo_ds['states']:
        state_item = Item(dataset=ds, ref=state['id'], name=state.get('name') or state.get('nameEN') or state.get('nameCN') or "")
        items_info_by_ref[state_item.ref] = ItemInfo(
            id=None,
            type='state',
            parent_ref=state.get('parentId'),
            names={
                'FR': state.get('name') or "",
                'EN': state.get('nameEN') or "",
                'CN': state.get('nameCN') or "",
            }
        )
        items.append(state_item)
    for hazo_ch in hazo_ds['characters']:
        item = Item(dataset=ds, ref=hazo_ch['id'], name=hazo_ch['name'])
        items_info_by_ref[item.ref] = ItemInfo(
            id=None,
            type='character',
            parent_ref=hazo_ch.get('parentId'),
            names={
                'EN': hazo_ch['nameEN'],
                'CN': hazo_ch['nameCN'],    
            },
            states_refs=hazo_ch['states'],
        )
        items.append(item)
        hierarchical_item.append(item)
    for hazo_taxon in hazo_ds['taxons']:
        item = Item(dataset=ds, ref=hazo_taxon['id'], name=hazo_taxon['name'])
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
            states_refs=states_refs,
            author=hazo_taxon['author'],
            detail=hazo_taxon['detail'],
        )
        items.append(item)
        hierarchical_item.append(item)
    Item.objects.bulk_create(items)
    characters = []
    taxons = []
    states_by_id = {}
    names = []
    hierarchies = []
    taxon_states = []
    for item in Item.objects.filter(dataset__id=ds.id):
        hierarchies.append(Hierarchy(ancestor=item, descendant=item, length=0))
        info = items_info_by_ref.get(item.ref)
        if info is None:
            continue
        info.id = item.id
        for lang_code, value in info.names.items():
            item_name = ItemName(item=item, text=value)
            item_name.lang_id = lang_code
            names.append(item_name)
    hierarchies_self = []
    for h_item in hierarchical_item:
        item_id = items_info_by_ref[h_item.ref].id
        item = Item(id=item_id)
        hierarchies_self.append(Hierarchy(ancestor=item, descendant=item, length=0))
    Hierarchy.objects.bulk_create(hierarchies_self)
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
        elif info.type == 'taxon':
            taxon = Taxon(author=info.author, description=info.detail)
            taxon.item_id = info.id
            taxons.append(taxon)
            for state_ref in info.states_refs:
                ts = TaxonState()
                ts.taxon_id = info.id
                ts.state_id = items_info_by_ref[state_ref].id
                taxon_states.append(ts)
        if info.parent_ref is not None:
            parent_id = items_info_by_ref[info.parent_ref].id
            h = Hierarchy.objects.filter(descendant_id=parent_id)
            nodes_to_item = []
            for child_node in h:
                node = Hierarchy(ancestor=child_node.ancestor, length=child_node.length + 1)
                node.descendant_id = info.id
                nodes_to_item.append(node)
            Hierarchy.objects.bulk_create(nodes_to_item)
    ItemName.objects.bulk_create(names)
    Character.objects.bulk_create(characters)
    Taxon.objects.bulk_create(taxons)
    State.objects.bulk_create(states_by_id.values())
    TaxonState.objects.bulk_create(taxon_states)

def import_hazo(src: pathlib.Path):
    with src.open("r") as input:
        _import_dataset(src, input)