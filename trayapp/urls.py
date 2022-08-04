from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
# from django.urls import path
from graphene_file_upload.django import FileUploadGraphQLView
# from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt

from django_distill import distill_path as path

urlpatterns = [
    path('admin/', admin.site.urls),
    path("graphql/", csrf_exempt(FileUploadGraphQLView.as_view(graphiql=True))),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
