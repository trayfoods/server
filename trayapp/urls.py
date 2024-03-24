from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from graphene_file_upload.django import FileUploadGraphQLView

# from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt
from .views import index_view, admin_ping
from core.views import order_redirect_share_view

# from users.views import get_bank_list

urlpatterns = [
    path("admin/host/ping", admin_ping, name="admin-ping"),
    path("admin/", admin.site.urls, name="admin"),
    path("", index_view, name="index"),
    path("api/", include("core.urls"), name="rest-api"),
    path("users/", include("users.urls"), name="users-api"),
    path(
        "graphql/",
        csrf_exempt(FileUploadGraphQLView.as_view(graphiql=True)),
        name="graph-api",
    ),
    path("pay/<str:order_id>", order_redirect_share_view, name="share-order"),
    # path("bank_list/", get_bank_list, name="bank_list"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
