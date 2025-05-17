from django.shortcuts import render

# Create your views here.

def index_view(request):
    """
    View function for the main page of the weather comparer.
    Renders the index.html template.
    """
    # Later, we will pass data to the template through the 'context' dictionary
    context = {}
    return render(request, 'comparer/index.html', context)