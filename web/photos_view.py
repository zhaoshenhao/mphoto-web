import logging
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Photo
from .utils.tools import get_events, get_view_link, get_dt_params
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
    draw, start, length, search_value, order = get_dt_params(request)
    event_id = request.POST.get("event_id")

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

    data = []
    for p in queryset:
        data.append({
            'event__name': p.event.name,
            'cloud_storage_id': p.cloud_storage_id,
            'cloud_storage__url': p.cloud_storage.url,
            'id': p.id,
            'name': p.name,
            'gdid': p.gdid,
            'full': get_view_link(p),
            'size': p.size,
            'status': Photo.STATUS_CHOICES[p.status][1],
            'modified_time': p.modified_time.strftime('%Y-%m-%d %H:%M:%S'),
            'created_time': p.created_time.strftime('%Y-%m-%d %H:%M:%S'),
            'last_updated': p.last_updated.strftime('%Y-%m-%d %H:%M:%S')
        })

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
