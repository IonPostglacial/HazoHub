from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http.response import Http404
from django.shortcuts import render

from . import utils
from ..models import Character, Dataset, FileSharing, Hierarchy, State, TaxonState


@login_required
def list_view(req: HttpRequest, file_name: str, in_character: int = 0):
    selected_states_ids = req.session.get('selected_states')
    if selected_states_ids is None:
        selected_states_ids = set()
    else:
        selected_states_ids = set(selected_states_ids)
    if 'unselect-all-state' in req.POST:
        selected_states_ids = []
        req.session['selected_states'] = []
    if 'select-state' in req.POST:
        selected_states_ids.add(req.POST['select-state'])
        req.session['selected_states'] = list(selected_states_ids)
    if 'unselect-state' in req.POST:
        selected_states_ids.remove(req.POST['unselect-state'])
        req.session['selected_states'] = list(selected_states_ids)
    if file_name.endswith("json"):
        file_path = utils.user_file_path(req.user, file_name)
    else:
        file_sharing = FileSharing.objects.filter(share_link=file_name).first()
        if not utils.user_can_access_file(req.user, file_sharing) or file_sharing is None:
            raise Http404("Not found")
        else:
            file_path = file_sharing.file_path
    dataset: Dataset = Dataset.objects.filter(src=file_path).first()
    if dataset is None:
        raise Http404(f"There is no dataset named {file_path}")
    selected_states = State.objects.select_related('item').filter(item_id__in=selected_states_ids).values('item_id', 'item__name')
    matching_taxons = TaxonState.objects.select_related('taxon', 'taxon__item').filter(state__item__dataset=dataset)
    for state in selected_states_ids:
        matching_taxons = matching_taxons.filter(state=state)
    matches = []
    for taxon_state in matching_taxons:
        matches.append({ 'name': taxon_state.taxon.item.name, 'id': taxon_state.taxon.item.id })
    chars = []
    if in_character == 0:
        characters = filter(lambda c: c.item.ancestors.count() == 1, Character.objects.filter(item__dataset=dataset))
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
        'matches': matches,
        'selected_states': selected_states,
    })

@login_required
def states_list(req: HttpRequest, file_name: str, in_character: int):
    file_path = utils.user_file_path(req.user, file_name)
    dataset: Dataset = Dataset.objects.filter(src=file_path).first()
    selected_states = req.session.get('selected_states')
    if selected_states is None:
        selected_states = []
    character_states = State.objects.filter(item__dataset=dataset).filter(character_id=in_character)
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