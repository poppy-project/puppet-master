import os
from django.shortcuts import render
from .models import Info

# Create your views here.

# Load the context for all the views here :
context = {'info' : Info.objects.get(), 'url_for_index' : '/'}

def index(request):
    return render(request, 'index.html',context)

def snap(request):
    # Adding new context specific to the view here :
    context.update({'iframe_src' : '../static/snap/snap.html' })
    return render(request, 'base-iframe.html', context)
	
def index_(request):
    return render(request, 'index_.html')

def juju(request):
    
    context = {'scheme' : request.scheme, 'host' : request.get_host(), 'path' : request.path, 'full' : request.get_full_path(), 'get' : request.GET, 'post' : request.POST, 'configfile' : configfile }
   
    return render(request, 'juju.html', context)

def juju2(request):
    
    context = {'scheme' : request.scheme, 'host' : request.get_host(), 'path' : request.path, 'full' : request.get_full_path(), 'get' : request.GET, 'post' : request.POST, 'configfile' : configfile }
   
    return render(request, './static-snap/snap.html', context)