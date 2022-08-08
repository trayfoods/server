from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
# from django.urls import path
from graphene_file_upload.django import FileUploadGraphQLView
# from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt
from .views import index_view
from django_distill import distill_path as path

urlpatterns = [
    path('admin/', admin.site.urls, name="admin"),
    path('', index_view, name="index"),
    path("graphql/", csrf_exempt(FileUploadGraphQLView.as_view(graphiql=True)), name="api"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
