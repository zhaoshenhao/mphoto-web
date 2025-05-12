import logging
import random
import requests
from django.utils.timezone import now
from django.db.models import Q, Count, Sum
from ..models import Event, Photo, BibPhoto, FacePhoto
import settings
from google.oauth2 import credentials
from googleapiclient.discovery import build


def build_gphoto_service():
    creds = credentials.Credentials.from_authorized_user_file(settings.GPHOTO_TOKEN_JSON, scopes=[
        'https://www.googleapis.com/auth/photoslibrary.readonly'])
    return build('photoslibrary', 'v1', credentials=creds, static_discovery=False)

def get_dt_params(request):
    draw = int(request.POST.get('draw', 1))
    start = int(request.POST.get('start', 0))
    length = int(request.POST.get('length', 10))
    search_value = request.POST.get('search[value]', '').strip()
    order_column_idx = request.POST.get("order[0][column]")
    order_column = request.POST.get(f"columns[{order_column_idx}][data]", "id")
    order_dir = request.POST.get("order[0][dir]", "asc")
    order = f"{'' if order_dir == 'asc' else '-'}{order_column}"
    return draw, start, length, search_value, order

def get_events(request):
    if request.user.role == 'admin':
        return Event.objects.all().order_by('name')
    else:
        return Event.objects.filter(eventmanager__user=request.user).order_by('name')

def generate_unique_code(event_id, existing_codes):
    while True:
        code = f"{random.randint(0, 9999999999):010}"
        if code not in existing_codes:
            existing_codes.add(code)
            return code

def get_all_events(request):
    return Event.objects.filter(enabled=True, expiry__gt=now()).order_by('name')

def human_file_size(num, si=False, dp=1):
    if not num:
        return "0B"
    thresh = 1000 if si else 1024
    if abs(num) < thresh:
        return f"{num} B"
    units = ["kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"] if si else \
            ["KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    u = -1
    r = 10 ** dp
    while abs(num) >= thresh and u < len(units) - 1:
        num /= thresh
        u += 1
    return f"{num:.{dp}f} {units[u]}"

def format_big_integer(n):
    if not n:
        return "0"
    return "{:,}".format(n)

def detect_url_type(url):
    if url.startswith('https://drive.google.com/drive/'):
        return 1 # Google Drive
    if url.startswith('https://photos.google.com/lr/album'):
        return 2 # Google Photos
    return 1

def detect_url_type_name(url):
    type = detect_url_type(url)
    if type == 1:
        return 'Google Drive'
    if type == 2:
        return 'Google Photos'
    return 'Unknown'

def get_links(storage_type, gdid, base_url, refresh: False):
    if storage_type == 1:
        return f'https://drive.google.com/thumbnail?id={gdid}&sz=w300', f"https://drive.google.com/uc?id={gdid}&export=download"
    if storage_type == 2:
        if refresh:
            base_url = get_base_url_by_id(gdid)
            return f"{base_url}=w300-h398", f"{base_url}=d"
        else:
            return f"{base_url}=w300-h398", f"{base_url}=d"
    return '#', '#'

def get_photo_links(p: Photo, refresh: False):
    return get_links(p.storage_type, p.gdid, p.base_url, refresh)

def get_view_link(p: Photo):
    if p.storage_type == 1:
        return f'https://drive.google.com/uc?export=view&id={p.gdid}'
    if p.storage_type == 2:
        return p.base_url
    return '#'

def get_base_url_by_id(media_id):
    service = build_gphoto_service()
    ret = service.mediaItems().get(mediaItemId=media_id).execute()
    return ret['baseUrl']

def verify_recaptcha(token, secret_key):
    url = 'https://www.google.com/recaptcha/api/siteverify'
    data = {
        'secret': secret_key,  #  Your reCAPTCHA secret key (server-side!)
        'response': token
    }
    response = requests.post(url, data=data)
    result = response.json()
    logging.info(result)
    return result.get('success', False)

def get_cloud_storage_stats(cs):
    photo_new = Photo.objects.filter(cloud_storage=cs, status=0).count()
    photo_done = Photo.objects.filter(cloud_storage=cs, status=1).count()
    photo_update = Photo.objects.filter(cloud_storage=cs, status=2).count()
    photo_stats = Photo.objects.filter(cloud_storage=cs).aggregate(
        total_count=Count('id'),
        total_size=Sum('size')
    )
    bib_photo_count = BibPhoto.objects.filter(photo__cloud_storage=cs).count()
    face_photo_count = FacePhoto.objects.filter(photo__cloud_storage=cs).count()
    return photo_stats['total_count'], photo_stats['total_size'], photo_new, photo_done, photo_update, bib_photo_count, face_photo_count
