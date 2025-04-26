import random
from django.utils.timezone import now
from ..models import Event, Photo


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

def get_links(storage_type, gdid, base_url):
    if storage_type == 1:
        return f'https://drive.google.com/thumbnail?id={gdid}&sz=w300', f"https://drive.google.com/uc?id={gdid}&export=download"
    if storage_type == 2:
        return f"{base_url}=w300-h398", f"{base_url}=d"
    return '#', '#'

def get_photo_links(p: Photo):
    if p.storage_type == 1:
        return f'https://drive.google.com/thumbnail?id={p.gdid}&sz=w300', f"https://drive.google.com/uc?id={p.gdid}&export=download"
    if p.storage_type == 2:
        return f"{p.base_url}=w300-h398", f"{p.base_url}=d"
    return '#', '#'
