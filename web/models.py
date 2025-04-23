# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils.timezone import now
from datetime import timedelta
from pgvector.django import VectorField
import random


class Bib(models.Model):
    event = models.ForeignKey('Event', models.DO_NOTHING)
    bib_number = models.CharField(max_length=10)
    enabled = models.BooleanField(default=True)
    name = models.CharField(max_length=100)
    code = models.CharField(unique=True, max_length=20, default=f"{random.randint(0, 9999999999):010d}")
    expiry = models.DateTimeField(default=now() + timedelta(days=365))

    class Meta:
        managed = False
        db_table = 'bib'
        unique_together = (('event', 'bib_number'),)


class BibPhoto(models.Model):
    photo = models.ForeignKey('Photo', on_delete=models.CASCADE)
    bib_number = models.CharField(max_length=10)
    event = models.ForeignKey('Event', models.DO_NOTHING)
    confidence = models.FloatField()

    class Meta:
        managed = False
        db_table = 'bib_photo'


class CloudStorage(models.Model):
    event = models.ForeignKey('Event', models.DO_NOTHING)
    url = models.CharField(unique=True, max_length=200)
    recursive = models.BooleanField()
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cloud_storage'


class Event(models.Model):
    current_date = now()
    future_date = current_date + timedelta(days=90)
    name = models.CharField(unique=True, max_length=100)
    enabled = models.BooleanField(default=True)
    expiry = models.DateTimeField(default=future_date)

    class Meta:
        managed = False
        db_table = 'event'

    def __str__(self):
        return self.name


class EventManager(models.Model):
    user = models.ForeignKey('User', models.DO_NOTHING)
    event = models.ForeignKey(Event, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'event_manager'
        unique_together = (('user', 'event'),)


class FacePhoto(models.Model):
    event = models.ForeignKey(Event, models.DO_NOTHING)
    photo = models.ForeignKey('Photo', on_delete=models.CASCADE)
    embedding = VectorField(dimensions=512)
    confidence = models.FloatField()

    class Meta:
        managed = False
        db_table = 'face_photo'


class Photo(models.Model):
    STATUS_CHOICES = [
        (0, 'New'),
        (1, 'Complete'),
        (2, 'Needs Update'),
    ]
    event = models.ForeignKey(Event, models.DO_NOTHING)
    name = models.CharField(max_length=100)
    last_updated = models.DateTimeField(auto_now=True)
    size = models.IntegerField()
    gdid = models.CharField(max_length=100)
    created_time = models.DateTimeField()
    modified_time = models.DateTimeField()
    cloud_storage = models.ForeignKey(CloudStorage, models.DO_NOTHING)
    status =  models.SmallIntegerField(choices=STATUS_CHOICES)

    class Meta:
        managed = False
        db_table = 'photo'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    email = models.CharField(unique=True, max_length=100)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=10)
    description = models.TextField(blank=True, null=True)
    created_timestamp = models.DateTimeField(auto_now_add=True)
    updated_timestamp = models.DateTimeField(auto_now=True)
    enabled = models.BooleanField()
    password = models.CharField(max_length=200)
    api_key = models.CharField(max_length=20, blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        managed = False
        db_table = 'user'

    def __str__(self):
        return self.email

    @property
    def is_active(self):
        return self.enabled

    @property
    def is_superuser(self):
        return self.role == 'admin'

    @property
    def is_staff(self):
        return self.role == 'admin'

    @property
    def is_authenticated(self):
        return True  # Always True for logged-in users

    @property
    def is_anonymous(self):
        return False  # Always False for logged-in users

    def has_perm(self, perm, obj=None):
        return self.role == 'admin'

    def has_module_perms(self, app_label):
        return self.role == 'admin'