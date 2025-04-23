from django.contrib import admin
from .models import Event, Bib, Photo, BibPhoto, FacePhoto, EventManager, CloudStorage

# Register your models here.
admin.site.register(Photo)
admin.site.register(BibPhoto)
admin.site.register(FacePhoto)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'enabled', 'expiry']
    list_filter = ['enabled', 'expiry']
    search_fields = ['name', 'enabled', 'expiry']
    ordering = ['name']

@admin.register(EventManager)
class EventManagerAdmin(admin.ModelAdmin):
    list_display = ['event', 'id', 'user']
    list_filter = ['event', 'user']
    search_fields = ['event', 'user']
    ordering = ['event']


@admin.register(Bib)
class BibAdmin(admin.ModelAdmin):
    list_display = ['event', 'id', 'bib_number', 'name', 'code', 'enabled', 'expiry']
    list_filter = ['event', 'enabled', 'expiry']
    search_fields = ['event', 'bib_number', 'name', 'code', 'enabled', 'expiry']
    ordering = ['bib_number']

@admin.register(CloudStorage)
class CloudStorageAdmin(admin.ModelAdmin):
    list_display = ['event', 'id', 'url', 'recursive', 'description']
    list_filter = ['event', 'recursive']
    search_fields = ['event', 'url', 'recursive', 'description']
    ordering = ['url']

