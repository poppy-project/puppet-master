from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

# Create your models here.

# Informations about the robot you want to run on your board
@python_2_unicode_compatible  # only if you need to support Python 2
class Robot(models.Model):
    host = models.CharField(max_length=200)
    creature = models.CharField(max_length=200)
    camera = models.BooleanField(default=True)
    def __str__(self):
        return self.host

# Informations about the board you are using and the version of the webapp
@python_2_unicode_compatible  # only if you need to support Python 2
class Info(models.Model):
    version = models.CharField(max_length=10)
    board = models.CharField(max_length=200, default='Raspberry Pi')
    def __str__(self):
        return 'v{} on {}'.format(self.version, self.board)

# Informations about the process launched (rest server / snap server / update process) usefull to have logs and to kill the process when the system need to clean 		
@python_2_unicode_compatible  # only if you need to support Python 2
class Daemon(models.Model):
    pid = models.IntegerField()
    log = models.TextField()
    def __str__(self):
        return self.pid