from django.conf import settings
from django.contrib import admin
from django.urls import include, path

# from django.views.generic.base import RedirectView

urlpatterns = [
    path("__reload__/", include("django_browser_reload.urls")),
    path("__api-auth__/", include("rest_framework.urls")),
    path("admin/", admin.site.urls),
    path("", include("app.main.urls")),
    # path("", RedirectView.as_view(url="/admin", permanent=False), name="root-redirect"),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
