from django.contrib import admin

# Register your models here.

from .models import Robot, Info, Daemon

admin.site.register(Robot)
admin.site.register(Info)
admin.site.register(Daemon)