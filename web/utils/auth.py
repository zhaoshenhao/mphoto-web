# utils/auth.py
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from web.models import EventManager, CloudStorage, User, Event, BibPhoto, FacePhoto, Bib, Photo

def user_has_event_permission(user, obj, raise_exception=True) -> bool:
    if user.is_superuser or not obj:
        return True
    # Get associated event_id based on the object type
    if isinstance(obj, Event):
        event_id = obj.id
    elif isinstance(obj, CloudStorage):
        event_id = obj.event_id
    elif isinstance(obj, BibPhoto):
        event_id = obj.event_id
    elif isinstance(obj, FacePhoto):
        event_id = obj.event_id
    elif isinstance(obj, Bib):
        event_id = obj.event_id
    elif isinstance(obj, Photo):
        event_id = obj.event_id
    else:
        return False  # Unsupported object type
    # Check if user is manager of this event
    if not EventManager.objects.filter(user=user, event_id=event_id).exists():
        if raise_exception:
            raise PermissionDenied()
        else:
            return False
    return True

def require_api_key(view_func):
    def wrapped_view(request, *args, **kwargs):
        api_key = request.headers.get('X-API-KEY') or request.GET.get('api_key')
        if not api_key:
            return JsonResponse({'error': 'API key required'}, status=401)
        try:
            request.api_user = User.objects.get(api_key=api_key, enabled=True)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Invalid API key'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapped_view
