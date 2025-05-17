from django.urls import path
from . import views  # Import views from the current app

app_name = 'comparer'  # Namespacing URLs

urlpatterns = [
    path('', views.index_view, name='index'),
    # '' means the root URL of this app (e.g., /weather/)
    # views.index_view is the function to call
    # name='index' is a unique name for this URL pattern
]