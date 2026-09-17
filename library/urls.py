from django.urls import path
from django.contrib.auth import views as auth_views
from library import views
from library.forms import StyledAuthenticationForm

urlpatterns = [
    # Auth
    path("login/", auth_views.LoginView.as_view(
        template_name="registration/login.html",
        authentication_form=StyledAuthenticationForm,
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("password-change/", auth_views.PasswordChangeView.as_view(template_name="registration/password_change.html"), name="password_change"),
    path("password-change/done/", auth_views.PasswordChangeDoneView.as_view(template_name="registration/password_change_done.html"), name="password_change_done"),

    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),

    # Books
    path("buku/", views.BookListView.as_view(), name="book-list"),
    path("buku/tambah/", views.BookCreateView.as_view(), name="book-create"),
    path("buku/<int:pk>/", views.BookDetailView.as_view(), name="book-detail"),
    path("buku/<int:pk>/edit/", views.BookUpdateView.as_view(), name="book-update"),
    path("buku/<int:pk>/hapus/", views.BookDeleteView.as_view(), name="book-delete"),

    # Profile & Settings
    path("profil/", views.ProfileView.as_view(), name="profile"),
    path("profil/edit/", views.ProfileUpdateView.as_view(), name="profile-update"),
    path("pengaturan/", views.SettingsView.as_view(), name="settings"),

    # Pengaturan → Kelola Pengguna (khusus staff/admin)
    path("pengguna/", views.UserManagementView.as_view(), name="user-list"),
    path("pengguna/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user-update"),
    path("pengguna/<int:pk>/hapus/", views.UserDeleteView.as_view(), name="user-delete"),

    # Identitas aplikasi (judul dinamis) — hanya admin
    path("pengaturan/identitas/", views.AppIdentityUpdateView.as_view(), name="app-identity"),

    # Tambah cepat (modal di form buku) — balas JSON
    path("api/genre/tambah/", views.GenreQuickCreateView.as_view(), name="genre-quick-create"),
    path("api/rak/tambah/", views.ShelfQuickCreateView.as_view(), name="shelf-quick-create"),

    # Cetak label buku 2 × 3 cm
    path("label/", views.LabelSelectView.as_view(), name="label-select"),
    path("label/cetak/", views.LabelPrintView.as_view(), name="label-print"),

    # Cetak label rak 3 × 4 cm / 4 × 6 cm
    path("label-rak/", views.ShelfLabelSelectView.as_view(), name="shelf-label-select"),
    path("label-rak/cetak/", views.ShelfLabelPrintView.as_view(), name="shelf-label-print"),

    # Pengaturan → master data DINAMIS: Genre / Kategori
    path("pengaturan/genre/tambah/", views.GenreCreateView.as_view(), name="genre-create"),
    path("pengaturan/genre/<int:pk>/edit/", views.GenreUpdateView.as_view(), name="genre-update"),
    path("pengaturan/genre/<int:pk>/hapus/", views.GenreDeleteView.as_view(), name="genre-delete"),

    # Pengaturan → master data DINAMIS: Lokasi Rak Buku
    path("pengaturan/rak/tambah/", views.ShelfCreateView.as_view(), name="shelf-create"),
    path("pengaturan/rak/<int:pk>/edit/", views.ShelfUpdateView.as_view(), name="shelf-update"),
    path("pengaturan/rak/<int:pk>/hapus/", views.ShelfDeleteView.as_view(), name="shelf-delete"),

    # API endpoints (charts, autocomplete)
    path("api/stats/", views.StatsAPIView.as_view(), name="api-stats"),
    path("api/books/", views.BookListAPIView.as_view(), name="api-book-list"),
    path("api/titles/", views.TitleAutocompleteAPIView.as_view(), name="api-title-autocomplete"),

    # Penjaga sesi (dipanggil skrip di base.html saat pengguna beraktivitas)
    path("api/sesi/ping/", views.SesiPingView.as_view(), name="sesi-ping"),
]
