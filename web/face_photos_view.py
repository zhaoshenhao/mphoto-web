import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render
from .models import FacePhoto
from .utils.tools import get_events
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
    draw = int(request.POST.get('draw', 1))
    start = int(request.POST.get('start', 0))
    length = int(request.POST.get('length', 10))
    event_id = request.POST.get('event_id')
    search_value = request.POST.get('search[value]', '').strip()

    order_column_idx = request.POST.get("order[0][column]")
    order_column = request.POST.get(f"columns[{order_column_idx}][data]", "id")
    order_dir = request.POST.get("order[0][dir]", "asc")
    order = f"{'' if order_dir == 'asc' else '-'}{order_column}"

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

    data = [{
        'event_id': bp.event_id,
        'event__name': bp.event.name,
        'id': bp.id,
        'photo_id': bp.photo_id,
        'confidence': f"{bp.confidence:.2f}",
        'photo__name': bp.photo.name,
        'photo__thumb_link': bp.photo.thumb_link,
        'photo__content_link': bp.photo.content_link,
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
def delete_face_photo(request, face_photo_id):
    face_photo = get_object_or_404(FacePhoto, pk=face_photo_id)
    user_has_event_permission(request.user, face_photo)

    face_photo.delete()
    return JsonResponse({'message': 'Deleted successfully'})
