import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render
from .models import FacePhoto
from .utils.tools import get_events, get_photo_links, get_dt_params
from .utils.auth import user_has_event_permission


logger = logging.getLogger(__name__)


@login_required
def face_photos(request):
    events = get_events(request)
    return render(request, 'web_admin/face_photos.html', {
        'events': events,
        'page_title': 'Face Photos'
    })

@login_required
@require_POST
@csrf_exempt
def face_photos_data(request):
    draw, start, length, search_value, order = get_dt_params(request)
    event_id = request.POST.get('event_id')

    queryset = FacePhoto.objects.only(
        'id', 'confidence', 'photo_id', 'photo__name', 'photo__last_updated', 'event__id', 'event__name'
        ).select_related('photo', 'event')

    if request.user.role != 'admin':
        queryset = queryset.filter(event__eventmanager__user=request.user)
    
    if event_id:
        queryset = queryset.filter(event_id=event_id)

    if search_value:
        queryset = queryset.filter(
            Q(photo__name__icontains=search_value) |
            Q(photo__event__name__icontains=search_value)
        )

    total_records = queryset.count()
    queryset = queryset.order_by(order)[start:start + length]

    data = []
    for bp in queryset:
        tl, dl = get_photo_links(bp.photo)
        data.append({
            'event_id': bp.event_id,
            'event__name': bp.event.name,
            'id': bp.id,
            'photo_id': bp.photo_id,
            'confidence': f"{bp.confidence:.2f}",
            'photo__name': bp.photo.name,
            'photo__thumb_link': tl,
            'photo__content_link': dl,
            'photo__modified_time': bp.photo.modified_time,
            'photo__last_updated': bp.photo.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data
    })

@login_required
def delete_face_photo(request, face_photo_id):
    face_photo = get_object_or_404(FacePhoto, pk=face_photo_id)
    user_has_event_permission(request.user, face_photo)

    face_photo.delete()
    return JsonResponse({'message': 'Deleted successfully'})
