from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
	url(r'^snap/', views.snap, name='snap'),
	url(r'^juju/', views.juju, name='juju'),
	url(r'^juju2/', views.juju2, name='juju2'),
	url(r'^index_/$', views.index_, name='poppy'),	
]