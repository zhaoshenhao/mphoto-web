import logging
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Photo
from .utils.tools import get_events
from .utils.auth import user_has_event_permission

logger = logging.getLogger(__name__)


@login_required
def photos(request):
    events = get_events(request)
    return render(request, 'web_admin/photos.html', {
        'events': events,
        'page_title': 'Photos'
    })

@login_required
@require_POST
@csrf_exempt
def photos_data(request):
    draw = int(request.POST.get("draw", 1))
    start = int(request.POST.get("start", 0))
    length = int(request.POST.get("length", 10))
    event_id = request.POST.get("event_id")
    search_value = request.POST.get("search[value]", "").strip()

    order_column_idx = request.POST.get("order[0][column]")
    order_column = request.POST.get(f"columns[{order_column_idx}][data]", "id")
    order_dir = request.POST.get("order[0][dir]", "asc")
    order = f"{'' if order_dir == 'asc' else '-'}{order_column}"

    queryset = Photo.objects.select_related('event')

    if request.user.role != 'admin':
        queryset = queryset.filter(event__eventmanager__user=request.user)

    if event_id:
        queryset = queryset.filter(event_id=event_id)

    if search_value:
        queryset = queryset.filter(
            Q(name__icontains=search_value) |
            Q(event__name__icontains=search_value)
        )

    total_records = queryset.count()
    queryset = queryset.order_by(order)[start:start + length]

    data = [{
        'event__name': p.event.name,
        'cloud_storage__url': p.cloud_storage.url,
        'id': p.id,
        'name': p.name,
        'gdid': p.gdid,
        'full': f"https://drive.google.com/uc?id={p.gdid}&export=download",
        'size': p.size,
        'status': Photo.STATUS_CHOICES[p.status][1],
        'modified_time': p.modified_time.strftime('%Y-%m-%d %H:%M:%S'),
        'created_time': p.created_time.strftime('%Y-%m-%d %H:%M:%S'),
        'last_updated': p.last_updated.strftime('%Y-%m-%d %H:%M:%S')
    } for p in queryset]

    return JsonResponse({
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data
    })

@login_required
@require_POST
def delete_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    user_has_event_permission(request.user, photo)
    photo.delete()
    messages.success(request, "Photo deleted.")
    return JsonResponse({'success': True})
