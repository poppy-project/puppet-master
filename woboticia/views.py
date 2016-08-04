from django.shortcuts import render

# Create your views here.

def index(request):
    return render(request, 'index.html')
    
    
def snap(request):
    context = {'nom' : 'JEHL' , 'prenom' : 'Julien' }
    return render(request, 'snap.html', context)
	
def index_(request):
    return render(request, 'index_.html')
	


