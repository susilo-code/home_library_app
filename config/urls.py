"""
URL configuration — Hirunaza's Library Information System

Catatan penting:
Rute autentikasi HANYA didefinisikan di library.urls (dengan form login ber-styling
StyledAuthenticationForm). `django.contrib.auth.urls` sengaja TIDAK di-include lagi
agar tidak ada duplikasi nama URL 'login' yang membuat template login kustom terabaikan.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("library.urls")),

    # Kompatibilitas: tautan lama /accounts/login/ → /login/
    path("accounts/login/", RedirectView.as_view(pattern_name="login", permanent=False)),
    path("accounts/logout/", RedirectView.as_view(pattern_name="logout", permanent=False)),
    path("accounts/password-change/", RedirectView.as_view(pattern_name="password_change", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
