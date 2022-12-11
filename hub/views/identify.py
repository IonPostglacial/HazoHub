from typing import Set, Optional

from django.db.models import Q, F, OuterRef, Subquery
from django.http import HttpRequest
from django.http.response import Http404
from django.shortcuts import render

from . import utils
from ..models import Character, CharacterInherentState, Dataset, DatasetVersion, FileSharing, Hierarchy, State, TaxonState


def file_path_from_name(req: HttpRequest, file_name: str) -> str:
    if file_name.endswith("json"):
        return utils.user_file_path(req.user, file_name)
    else:
        file_sharing = FileSharing.objects.filter(share_link=file_name).first()
        if not utils.user_can_access_file(req.user, file_sharing) or file_sharing is None:
            raise Http404("Not found")
        else:
            return file_sharing.file_path

def _get_matchin_taxons(version: DatasetVersion, selected_states_ids: list):
    inherent_states = CharacterInherentState.objects.filter(state__item_id__in=selected_states_ids)
    matching_taxons = TaxonState.from_dataset_version(version) \
        .select_related('taxon', 'taxon__item')
    for selected_state_id in selected_states_ids:
        try:
            inherent = inherent_states.get(state=selected_state_id)
        except CharacterInherentState.DoesNotExist:
            inherent = None
        if inherent is not None:
            ch_partof = Hierarchy.objects.filter(ancestor=inherent.character.item).values_list('item_id', flat=True)
        else:
            ch_partof = []
        matching_taxons = matching_taxons.filter(Q(state=selected_state_id) | Q(state__character__item__in=ch_partof))
    matches = matching_taxons.values('taxon__item_id')
    taxons_children = Hierarchy.objects \
        .filter(Q(ancestor__in=Subquery(matches))) \
        .select_related('item') \
        .values('descendant_id', 'descendant__name') \
        .annotate(id=F('descendant_id'), name=F('descendant__name'))
    return taxons_children

def list_view(req: HttpRequest, file_name: str, in_character: int = 0):
    selected_states_ids: Optional[Set[str]] = req.session.get('selected_states')
    if selected_states_ids is None:
        selected_states_ids = set()
    else:
        selected_states_ids = set(selected_states_ids)
    if 'unselect-all-state' in req.POST:
        selected_states_ids = set()
        req.session['selected_states'] = []
    if 'select-state' in req.POST:
        selected_states_ids.add(req.POST['select-state'])
        req.session['selected_states'] = list(selected_states_ids)
    if 'unselect-state' in req.POST:
        selected_states_ids.remove(req.POST['unselect-state'])
        req.session['selected_states'] = list(selected_states_ids)
    file_path = file_path_from_name(req, file_name)
    dataset: Dataset = Dataset.objects.filter(src=file_path).first()
    if dataset is None:
        raise Http404(f"There is no dataset named {file_path}")
    version = DatasetVersion.last_for_dataset(dataset)
    selected_states = State.objects.select_related('item', 'inherent_character') \
        .filter(item_id__in=selected_states_ids) \
        .values('item_id', 'item__name')
    matching_taxons = _get_matchin_taxons(version, selected_states_ids)
    chars = []
    if in_character == 0:
        characters = filter(lambda c: c.item.ancestors.count() == 1, Character.from_dataset_version(version))
        items = map(lambda ch: ch.item, characters)
    else:
        hierarchies = Hierarchy.objects.filter(length=1).filter(ancestor__id=in_character)
        items = map(lambda h: h.descendant, hierarchies)
    for item in items:
        imgs = item.pictures.all()
        img = ""
        if len(imgs) > 0:
            img = imgs[0].url
        chars.append({
            'id': item.id,
            'name': item.name,
            'img': img,
            'names': { item['lang']: item['text'] for item in item.itemname_set.all().values('lang', 'text') },
            'hasChildren': item.descendants.count() > 1,
        })

    return render(req, 'hub/char_list.html', { 
        'file_name': file_name,
        'toplevel': in_character == 0,
        'characters': chars,
        'matches': matching_taxons,
        'selected_states': selected_states,
    })

def states_list(req: HttpRequest, file_name: str, in_character: int):
    file_path = file_path_from_name(req, file_name)
    dataset: Dataset = Dataset.objects.filter(src=file_path).first()
    version = DatasetVersion.last_for_dataset(dataset)
    selected_states: Optional[Set[str]] = req.session.get('selected_states')
    if selected_states is None:
        selected_states = set()
    character_states = State.from_dataset_version(version).filter(character_id=in_character)
    states = []
    for s in character_states:
        imgs = s.item.pictures.all()
        img = ""
        if len(imgs) > 0:
            img = imgs[0].url
        states.append({
            'id': s.item.id,
            'name': s.item.name,
            'img': img,
            'names': { item['lang']: item['text'] for item in s.item.itemname_set.all().values('lang', 'text') },
        })
    return render(req, 'hub/char_states_list.html', { 
        'states': states,
        'file_name': file_name,
        'character': in_character,
    })