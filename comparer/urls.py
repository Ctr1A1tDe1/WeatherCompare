from django.urls import path
from . import views

app_name = "comparer"

urlpatterns = [
    path("", views.index_view, name="index"),
    # '' means the root URL of this app (e.g., /weather/)
    # views.index_view is the function to call
    # name='index' is a unique name for this URL pattern
]
