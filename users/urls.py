from django.urls import path
from users.views import get_filtered_campus

urlpatterns = [
    path("get-filtered-campus/", get_filtered_campus, name="get-filtered-campus"),
]