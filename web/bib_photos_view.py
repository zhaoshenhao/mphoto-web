import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render
from .models import BibPhoto
from .utils.auth import user_has_event_permission
from .utils.tools import get_events, get_dt_params


logger = logging.getLogger(__name__)

@login_required
def bib_photos(request):
    events = get_events(request)
    return render(request, 'web_admin/bib_photos.html', {
        'events': events,
        'page_title': 'Bib Photos'
    })

@login_required
@require_POST
@csrf_exempt
def bib_photos_data(request):
    draw, start, length, search_value, order = get_dt_params(request)
    event_id = request.POST.get('event_id')
    queryset = BibPhoto.objects.select_related('photo', 'event')
    if request.user.role != 'admin':
        queryset = queryset.filter(event__eventmanager__user=request.user)

    if event_id:
        queryset = queryset.filter(event_id=event_id)

    if search_value:
        queryset = queryset.filter(
            Q(bib_number__icontains=search_value) |
            Q(photo__name__icontains=search_value) |
            Q(event__name__icontains=search_value)
        )

    total_records = queryset.count()
    queryset = queryset.order_by(order)[start:start + length]

    data = [{
        'event_id': bp.event_id,
        'event__name': bp.event.name,
        'id': bp.id,
        'bib_number': bp.bib_number,
        'photo_id': bp.photo_id,
        'confidence': f"{bp.confidence:.2f}",
        'photo__name': bp.photo.name,
        'photo__thumb_link': f'https://drive.google.com/thumbnail?id={bp.photo.gdid}&sz=w300',
        'photo__content_link': f'https://drive.google.com/file/d/{bp.photo.gdid}/view',
        'photo__modified_time': bp.photo.modified_time,
        'photo__last_updated': bp.photo.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
    } for bp in queryset]

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data
    })

@login_required
def delete_bib_photo(request, bib_photo_id):
    bib_photo = get_object_or_404(BibPhoto, pk=bib_photo_id)
    user_has_event_permission(request.user, bib_photo)
    bib_photo.delete()
    return JsonResponse({'message': 'Deleted successfully'})
