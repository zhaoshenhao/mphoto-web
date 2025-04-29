import numpy as np
import json
import logging
import cv2
import base64
from typing import Dict
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

import settings
from .models import Event, EventManager, CloudStorage, Photo, BibPhoto, FacePhoto
from .utils.auth import require_api_key, user_has_event_permission
from .utils.search import search_bib, search_face, get_embeddings
from .utils.tools import detect_url_type, detect_url_type_name, verify_recaptcha


logger = logging.getLogger(__name__)

@require_GET
@require_api_key
def api_list_events(request):
    user = request.api_user
    name_filter = request.GET.get('name', '').strip()

    qs = Event.objects.filter(enabled=True, expiry__gt=now())
    if not user.is_superuser:
        event_ids = EventManager.objects.filter(user=user).values_list('event_id', flat=True)
        qs = qs.filter(id__in=event_ids)

    if name_filter:
        qs = qs.filter(name__icontains=name_filter)

    events = list(qs.values())
    return JsonResponse(events, safe=False)

@require_GET
@require_api_key
def api_event_detail(request, event_id):
    user = request.api_user
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)
    user_has_event_permission(user, event)
    if not user_has_event_permission(user, event, False):
        return JsonResponse({'error': 'Access denied'}, status=403)

    cloud_storages = list(CloudStorage.objects.filter(event=event).values())
    return JsonResponse({
        'event': {field.name: getattr(event, field.name) for field in event._meta.fields},
        'cloud_storages': cloud_storages
    })

@require_GET
@require_api_key
def api_cloud_storage_detail(request, cloud_storage_id):
    user = request.api_user
    cs = get_object_or_404(CloudStorage, id=cloud_storage_id)
    if not user_has_event_permission(user, cs, False):
        return JsonResponse({'error': 'Access denied'}, status=403)
    photo_count = Photo.objects.filter(cloud_storage=cs).count()
    photo_new = Photo.objects.filter(cloud_storage=cs, status=0).count()
    photo_done = Photo.objects.filter(cloud_storage=cs, status=1).count()
    photo_update = Photo.objects.filter(cloud_storage=cs, status=2).count()
    bib_photo_count = BibPhoto.objects.filter(photo__cloud_storage=cs).count()
    face_photo_count = FacePhoto.objects.filter(photo__cloud_storage=cs).count()
    jd = {
        'id': cs.id,
        'event_id': cs.event_id,
        'url': cs.url,
        'storage_type': detect_url_type(cs.url),
        'storage_type_name': detect_url_type_name(cs.url),
        'recursive': cs.recursive,
        'description': cs.description,
        'photo': {
            'total': photo_count,
            'new': photo_new,
            'complete': photo_done,
            'need_update': photo_update
        },
        'bib_photo_count': bib_photo_count,
        'face_photo_count': face_photo_count
    }
    return JsonResponse(jd)

@require_GET
@require_api_key
def api_list_photos(request, cloud_storage_id):
    user = request.api_user
    fmt = request.GET.get('format', 'compact')
    incomplete = request.GET.get('incomplete', 'false').lower() in ['1', 'true', 'yes']
    rows = int(request.GET.get('rows', 0))
    try:
        cloud = CloudStorage.objects.select_related('event').get(id=cloud_storage_id)
    except CloudStorage.DoesNotExist:
        return JsonResponse({'error': 'Cloud storage not found'}, status=404)
    if not user_has_event_permission(user, cloud, False):
        return JsonResponse({'error': 'Access denied'}, status=403)
    if incomplete:
        qs = Photo.objects.filter(cloud_storage=cloud, status__in=[0, 2])
    else:
        qs = Photo.objects.filter(cloud_storage=cloud)
    if rows != 0:
        ps = qs.order_by('-id')[:rows]
    else:
        ps = qs.order_by('-id')
    if fmt == 'compact':
        data = list(ps.values('id', 'name', 'last_updated', 'size', 'gdid', 'modified_time', 'status', 'storage_type', 'base_url'))
    else:
        data = list(ps.values())
    return JsonResponse(data, safe=False)

@api_view(['POST'])
@require_api_key
def api_save_photos(request, cloud_storage_id):
    cloud_storage = get_object_or_404(CloudStorage, id=cloud_storage_id)
    user_has_event_permission(request.api_user, cloud_storage)
    storage_type = detect_url_type(cloud_storage.url)
    try:
        only_new = json.loads(request.body)
        new_list = []
        for f in only_new:
            p = Photo(
                event = cloud_storage.event,
                name = f['name'],
                size = f['size'],
                gdid = f['gdid'],
                created_time = f['created_time'],
                modified_time = f['modified_time'],
                cloud_storage = cloud_storage,
                base_url = f['base_url'],
                storage_type = storage_type,
                status = 0
            )
            new_list.append(p)
            logger.info(f'Add new photo: {f["name"]} / {f["gdid"]}')
        Photo.objects.bulk_create(new_list, ignore_conflicts=True)
        return JsonResponse({'message': f'{len(new_list)} photos saved'}, status=201)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': str(e)}, status=500)
    
@api_view(['POST'])
@require_api_key
def api_update_photos(request, cloud_storage_id):
    cloud_storage = get_object_or_404(CloudStorage, id=cloud_storage_id)
    user_has_event_permission(request.api_user, cloud_storage)
    try:
        changed = json.loads(request.body)
        for c in changed:
            logger.info(f'Update photo: {c["name"]} / {c["gdid"]}')
            Photo.objects.filter(gdid=c['gdid']).update(
                status=2, # Need update
                size=c['size'],
                modified_time=c['modified_time']
            )
        updated_count = len(changed)
        return JsonResponse({'message': f'{updated_count} photos changed status to -1'}, status=200)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@require_api_key
def api_delete_photos(request, cloud_storage_id):
    cloud_storage = get_object_or_404(CloudStorage, id=cloud_storage_id)
    user_has_event_permission(request.api_user, cloud_storage)
    try:
        missing = json.loads(request.body)
        delete_count, type_counts = Photo.objects.filter(id__in=missing).delete()
        return JsonResponse({'photo_deleted': delete_count}, status=200)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@require_api_key
def api_add_photos_result(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    user_has_event_permission(request.api_user, photo)
    try:
        data = json.loads(request.body)
        photo_size = data['photo_size']
        bib_photos: Dict = data['bib_photos']
        bp_list = []
        for b in bib_photos:
            b = BibPhoto(
                photo = photo,
                event = photo.event,
                bib_number = b['bib_number'],
                confidence = b['confidence']
            )
            logger.info(f"Add bib photo: {b.bib_number}: {photo.name}")
            bp_list.append(b)
        logger.info("Delete old bib photos")
        bp_del_cnt, type_counts = BibPhoto.objects.filter(photo=photo).delete()
        logger.info("Save bib photos")
        BibPhoto.objects.bulk_create(bp_list, ignore_conflicts=True)
        fp_list = []
        face_photos: Dict = data['face_photos']
        for f in face_photos:
            f = FacePhoto(
                photo = photo,
                event = photo.event,
                embedding = np.array(f['embedding']),
                confidence = f['confidence']
            )
            fp_list.append(f)
            logger.info(f"Add face photo: {photo.name}")
        logger.info("Delete old face photos")
        fp_del_cnt, type_counts = FacePhoto.objects.filter(photo=photo).delete()
        logger.info("Save face photos")
        FacePhoto.objects.bulk_create(fp_list, ignore_conflicts=True)
        ret_data = {
            'bib_photo_added': len(bib_photos),
            'bib_photo_delete': bp_del_cnt,
            'face_photo_added': len(face_photos),
            'face_photo_delete': fp_del_cnt
        }
        logger.info("Update photo status")
        photo.status = 1 # Completed
        logger.info(f"Photo size: {photo_size}")
        if photo.storage_type == 2: # Update size for google photo
            logger.info(f"Update photo size: {photo_size}")
            photo.size = photo_size
        photo.save()
        return JsonResponse(ret_data, status=200)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
def search_photo(request,):
    try:
        data = json.loads(request.body)
        recaptcha_token = data['recaptcha_token']
        if not verify_recaptcha(recaptcha_token, settings.RECAPTCHA_SECRET_KEY):  # Replace with your secret key
            return JsonResponse({'error': 'Invalid reCAPTCHA'}, status=400)
        event_id = data['event_id']
        try:
            Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return JsonResponse({'error': 'Event not found'}, status=404)
        bib_number = str.strip(data['bib_number'])
        images = data['images']
        if not (bib_number or images):
            return JsonResponse([], status=200)
        ret = {}
        if bib_number:
            search_bib(ret, bib_number, event_id)
        if len(images) > 0:
            img_list = [cv2.imdecode(np.frombuffer(base64.b64decode(img.split(",")[1]), np.uint8), cv2.IMREAD_COLOR)
                  for img in images]
            embeddings = get_embeddings(img_list)
            for embedding in embeddings:
                search_face(ret, embedding, event_id)
        return JsonResponse(list(ret.values()), safe=False)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': str(e)}, status=500)
