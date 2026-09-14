import difflib
import json

from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    TemplateView, FormView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.shortcuts import redirect
from django.utils import timezone
from django.core.paginator import Paginator

from .models import ActivityLog, Book, Genre, Shelf, SiteConfig, UserProfile, normalize_text
from .forms import (BookForm, GenreForm, ProfileForm, ShelfForm, SiteConfigForm,
                    StaffUserCreateForm, StaffUserUpdateForm, UserSettingsForm)


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard utama dengan statistik, grafik, dan jam digital"""
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        total_books = Book.objects.count()
        total_genres = Genre.objects.count()
        total_users = User.objects.filter(recorded_books__isnull=False).distinct().count()

        my_books = Book.objects.filter(recorded_by=user).count()
        my_genres = Genre.objects.filter(books__recorded_by=user).distinct().count()

        # Distribusi genre untuk grafik donat — LENGKAP dengan persentase
        genre_qs = list(Genre.objects.annotate(book_count=Count('books')).order_by('-book_count'))
        total_genre_books = sum(g.book_count for g in genre_qs)
        distribusi = [
            {
                'name': g.name,
                'count': g.book_count,
                'percent': round(g.book_count / total_genre_books * 100, 1) if total_genre_books else 0.0,
                'color': g.color_code or '#8A4FFF',
            }
            for g in genre_qs if g.book_count
        ]
        # Donut: maksimal 8 genre, sisanya digabung jadi "Lainnya" agar tetap terbaca
        donut = distribusi[:8]
        sisa = distribusi[8:]
        if sisa:
            sisa_count = sum(d['count'] for d in sisa)
            donut.append({
                'name': 'Lainnya',
                'count': sisa_count,
                'percent': round(sisa_count / total_genre_books * 100, 1) if total_genre_books else 0.0,
                'color': '#94A3B8',
            })

        genre_labels = [d['name'] for d in donut]
        genre_counts = [d['count'] for d in donut]
        genre_colors = [d['color'] for d in donut]
        genre_percents = [d['percent'] for d in donut]

        # Top 5 genre berdasarkan jumlah buku (menggantikan grafik produktivitas kontributor)
        top5 = distribusi[:5]
        top_genre_labels = [d['name'] for d in top5]
        top_genre_counts = [d['count'] for d in top5]
        top_genre_colors = [d['color'] for d in top5]

        recent_activities = ActivityLog.objects.select_related('user').order_by('-timestamp')[:10]
        recent_books = Book.objects.select_related('genre', 'recorded_by', 'shelf').order_by('-created_at')[:5]

        # Komposisi jenis buku (Fiksi vs Non-Fiksi)
        fiksi = Book.objects.filter(book_type=Book.BookCategory.FIKSI).count()
        non_fiksi = Book.objects.filter(book_type=Book.BookCategory.NON_FIKSI).count()

        shelf_stats = Shelf.objects.annotate(book_count=Count('books')).order_by('-book_count')[:5]

        context.update({
            'total_books': total_books,
            'total_genres': total_genres,
            'total_users': total_users,
            'total_shelves': Shelf.objects.count(),
            'my_books': my_books,
            'my_genres': my_genres,
            'total_fiksi': fiksi,
            'total_non_fiksi': non_fiksi,
            'genre_labels': json.dumps(genre_labels),
            'genre_counts': json.dumps(genre_counts),
            'genre_colors': json.dumps(genre_colors),
            'genre_percents': json.dumps(genre_percents),
            'genre_distribution': distribusi,
            'top_genre_labels': json.dumps(top_genre_labels),
            'top_genre_counts': json.dumps(top_genre_counts),
            'top_genre_colors': json.dumps(top_genre_colors),
            'recent_activities': recent_activities,
            'recent_books': recent_books,
            'shelf_stats': shelf_stats,
        })
        return context


class BookListView(LoginRequiredMixin, ListView):
    """Data Table buku dengan filter, search, pagination"""
    model = Book
    template_name = "books/book_list.html"
    context_object_name = "books"
    paginate_by = 10

    def get_queryset(self):
        qs = Book.objects.select_related(
            'genre', 'shelf', 'recorded_by', 'recorded_by__profile'
        ).order_by('-created_at')

        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(author__icontains=search) |
                Q(isbn__icontains=search) |
                Q(recorded_by__username__icontains=search) |
                Q(shelf__name__icontains=search) |
                Q(genre__name__icontains=search)
            )

        genre = self.request.GET.get('genre')
        if genre:
            qs = qs.filter(genre__slug=genre)

        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        user_id = self.request.GET.get('user')
        if user_id:
            qs = qs.filter(recorded_by_id=user_id)

        shelf_id = self.request.GET.get('shelf')
        if shelf_id:
            qs = qs.filter(shelf_id=shelf_id)

        # Jenis buku: pilihan tetap Fiksi / Non-Fiksi
        book_type = self.request.GET.get('book_type')
        if book_type:
            qs = qs.filter(book_type=book_type)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genres'] = Genre.objects.filter(is_active=True)
        context['shelves'] = Shelf.objects.filter(is_active=True)
        context['book_type_choices'] = Book.BookCategory.choices
        context['status_choices'] = Book.ReadingStatus.choices
        context['users'] = User.objects.filter(recorded_books__isnull=False).distinct()
        context['current_filters'] = {
            'q': self.request.GET.get('q', ''),
            'genre': self.request.GET.get('genre', ''),
            'status': self.request.GET.get('status', ''),
            'user': self.request.GET.get('user', ''),
            'shelf': self.request.GET.get('shelf', ''),
            'book_type': self.request.GET.get('book_type', ''),
        }
        return context


class BookDetailView(LoginRequiredMixin, DetailView):
    model = Book
    template_name = "books/book_detail.html"
    context_object_name = "book"

    def get_queryset(self):
        return Book.objects.select_related('genre', 'shelf', 'recorded_by', 'recorded_by__profile')


class BookFormContextMixin:
    """
    Menyediakan flag untuk template form buku:
    section opsional otomatis TERBUKA bila ada error di dalamnya.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get('form')
        errors = form.errors if form is not None else {}
        context['detail_error'] = any(
            f in errors for f in ('isbn', 'publication_year', 'purchase_year', 'publisher', 'pages', 'rating')
        )
        context['cover_error'] = any(f in errors for f in ('cover_image', 'cover_url'))
        context['summary_error'] = 'summary' in errors
        return context


class BookCreateView(LoginRequiredMixin, BookFormContextMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = "books/book_form.html"
    success_url = reverse_lazy("book-list")

    def form_valid(self, form):
        if form.duplicate_warning and '_ignore_duplicate' not in self.request.POST:
            return self.render_to_response(
                self.get_context_data(form=form, ask_duplicate_confirmation=True)
            )

        form.instance.recorded_by = self.request.user
        messages.success(self.request, "Buku berhasil ditambahkan!")
        ActivityLog.objects.create(
            user=self.request.user,
            action="TAMBAH_BUKU",
            detail=f"Menambahkan buku: {form.instance.title}"
        )
        return super().form_valid(form)


class BookUpdateView(LoginRequiredMixin, BookFormContextMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = "books/book_form.html"
    success_url = reverse_lazy("book-list")

    def form_valid(self, form):
        if form.duplicate_warning and '_ignore_duplicate' not in self.request.POST:
            return self.render_to_response(
                self.get_context_data(form=form, ask_duplicate_confirmation=True)
            )

        messages.success(self.request, "Buku berhasil diperbarui!")
        ActivityLog.objects.create(
            user=self.request.user,
            action="UPDATE_BUKU",
            detail=f"Memperbarui buku: {form.instance.title}"
        )
        return super().form_valid(form)


class BookDeleteView(LoginRequiredMixin, DeleteView):
    model = Book
    template_name = "books/book_confirm_delete.html"
    success_url = reverse_lazy("book-list")

    def form_valid(self, form):
        book_title = self.object.title
        messages.success(self.request, f"Buku '{book_title}' berhasil dihapus!")
        ActivityLog.objects.create(
            user=self.request.user,
            action="HAPUS_BUKU",
            detail=f"Menghapus buku: {book_title}"
        )
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "accounts/profile.html"
    context_object_name = "profile_user"

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        my_books = Book.objects.filter(recorded_by=user).select_related('genre', 'shelf').order_by('-created_at')
        context['my_books'] = my_books
        context['my_stats'] = {
            'total_books': my_books.count(),
            'completed': my_books.filter(status=Book.ReadingStatus.COMPLETED).count(),
            'reading': my_books.filter(status=Book.ReadingStatus.READING).count(),
            'unread': my_books.filter(status=Book.ReadingStatus.UNREAD).count(),
            'genres': Genre.objects.filter(books__recorded_by=user).distinct().count(),
        }
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = ProfileForm
    template_name = "accounts/profile_form.html"
    success_url = reverse_lazy("profile")

    def get_object(self):
        return self.request.user.profile

    def form_valid(self, form):
        messages.success(self.request, "Profil berhasil diperbarui!")
        return super().form_valid(form)


class SettingsView(LoginRequiredMixin, FormView):
    """
    Halaman Pengaturan:
    - preferensi tema
    - master data DINAMIS: Genre/Kategori & Lokasi Rak Buku (CRUD via endpoint terpisah)
    """
    template_name = "accounts/settings.html"
    form_class = UserSettingsForm
    success_url = reverse_lazy("settings")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user.profile
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genres'] = Genre.objects.annotate(book_count=Count('books')).order_by('name')
        context['shelves'] = Shelf.objects.annotate(book_count=Count('books')).order_by('name')
        context['genre_form'] = GenreForm(prefix='genre')
        context['shelf_form'] = ShelfForm(prefix='shelf')
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Preferensi tema berhasil disimpan!")
        return super().form_valid(form)


# ─── Master data dinamis: Genre / Kategori ────────────────────────────────────

class GenreCreateView(LoginRequiredMixin, CreateView):
    model = Genre
    form_class = GenreForm
    template_name = "settings/genre_form.html"
    success_url = reverse_lazy("settings")

    def form_valid(self, form):
        messages.success(self.request, f'Genre "{form.instance.name}" berhasil ditambahkan.')
        ActivityLog.objects.create(user=self.request.user, action="TAMBAH_GENRE",
                                   detail=f"Menambahkan genre: {form.instance.name}")
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.POST.get('_inline') == '1':
            for field, errs in form.errors.items():
                label = form.fields[field].label if field in form.fields else field
                messages.error(self.request, f'{label}: {errs[0]}')
            return redirect('settings')
        return super().form_invalid(form)


class GenreUpdateView(LoginRequiredMixin, UpdateView):
    model = Genre
    form_class = GenreForm
    template_name = "settings/genre_form.html"
    success_url = reverse_lazy("settings")

    def form_valid(self, form):
        messages.success(self.request, f'Genre "{form.instance.name}" berhasil diperbarui.')
        return super().form_valid(form)


class GenreDeleteView(LoginRequiredMixin, DeleteView):
    model = Genre
    template_name = "settings/confirm_delete.html"
    success_url = reverse_lazy("settings")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['jenis'] = 'Genre / Kategori'
        context['kembali_url'] = reverse('settings')
        context['dampak'] = (
            f'{self.object.books.count()} buku memakai genre ini. '
            'Buku tidak terhapus — kolom genre-nya akan menjadi kosong.'
        )
        return context

    def form_valid(self, form):
        nama = self.object.name
        jumlah_buku = self.object.books.count()
        messages.success(self.request, f'Genre "{nama}" berhasil dihapus.')
        ActivityLog.objects.create(
            user=self.request.user, action="HAPUS_GENRE",
            detail=f"Menghapus genre: {nama} ({jumlah_buku} buku jadi tanpa genre)",
        )
        return super().form_valid(form)


# ─── Master data dinamis: Lokasi Rak Buku ─────────────────────────────────────

class ShelfCreateView(LoginRequiredMixin, CreateView):
    model = Shelf
    form_class = ShelfForm
    template_name = "settings/shelf_form.html"
    success_url = reverse_lazy("settings")

    def form_valid(self, form):
        messages.success(self.request, f'Lokasi rak "{form.instance.name}" berhasil ditambahkan.')
        ActivityLog.objects.create(user=self.request.user, action="TAMBAH_RAK",
                                   detail=f"Menambahkan lokasi rak: {form.instance.name}")
        return super().form_valid(form)

    def form_invalid(self, form):
        # Form cepat (inline) di halaman Pengaturan: kembali ke sana dengan pesan error
        if self.request.POST.get('_inline') == '1':
            for field, errs in form.errors.items():
                label = form.fields[field].label if field in form.fields else field
                messages.error(self.request, f'{label}: {errs[0]}')
            return redirect('settings')
        return super().form_invalid(form)


class ShelfUpdateView(LoginRequiredMixin, UpdateView):
    model = Shelf
    form_class = ShelfForm
    template_name = "settings/shelf_form.html"
    success_url = reverse_lazy("settings")

    def form_valid(self, form):
        messages.success(self.request, f'Lokasi rak "{form.instance.name}" berhasil diperbarui.')
        return super().form_valid(form)


class ShelfDeleteView(LoginRequiredMixin, DeleteView):
    model = Shelf
    template_name = "settings/confirm_delete.html"
    success_url = reverse_lazy("settings")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['jenis'] = 'Lokasi Rak Buku'
        context['kembali_url'] = reverse('settings')
        context['dampak'] = (
            f'{self.object.books.count()} buku memakai rak ini. '
            'Buku tidak terhapus — kolom rak-nya akan menjadi kosong.'
        )
        return context

    def form_valid(self, form):
        nama = self.object.name
        jumlah_buku = self.object.books.count()
        messages.success(self.request, f'Lokasi rak "{nama}" berhasil dihapus.')
        ActivityLog.objects.create(
            user=self.request.user, action="HAPUS_RAK",
            detail=f"Menghapus lokasi rak: {nama} ({jumlah_buku} buku jadi tanpa rak)",
        )
        return super().form_valid(form)


# ─── Manajemen pengguna (khusus admin/staff) ──────────────────────────────────

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Batasi akses hanya untuk staff/superuser."""

    def test_func(self):
        u = self.request.user
        return bool(u.is_authenticated and (u.is_staff or u.is_superuser))

    def handle_no_permission(self):
        # Sudah login tapi bukan staff -> kembalikan ke dashboard dengan pesan jelas
        if self.request.user.is_authenticated:
            messages.error(self.request, 'Halaman ini khusus administrator (staff).')
            return redirect('dashboard')
        return super().handle_no_permission()


class UserManagementView(StaffRequiredMixin, FormView):
    """
    Kelola pengguna aplikasi: daftar akun + form cepat menambah pengguna baru.

    GET  /pengguna/            -> daftar akun
    POST /pengguna/            -> tambah akun (form cepat)
    """
    template_name = "accounts/user_management.html"
    form_class = StaffUserCreateForm
    success_url = reverse_lazy("user-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.annotate(
            jumlah_buku=Count('recorded_books')
        ).order_by('-is_superuser', '-is_staff', 'username')
        context['total_aktif'] = User.objects.filter(is_active=True).count()
        context['total_nonaktif'] = User.objects.filter(is_active=False).count()
        context['total_staff'] = User.objects.filter(is_staff=True).count()
        return context

    def form_valid(self, form):
        pengguna = form.save()
        messages.success(
            self.request,
            f'Pengguna "{pengguna.username}" berhasil dibuat. '
            f'Minta yang bersangkutan login lalu ganti kata sandinya.'
        )
        ActivityLog.objects.create(
            user=self.request.user, action="TAMBAH_USER",
            detail=f"Membuat akun pengguna: {pengguna.username}",
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        for field, errs in form.errors.items():
            label = form.fields[field].label if field in form.fields else field
            messages.error(self.request, f'{label}: {errs[0]}')
        return super().form_invalid(form)


class UserUpdateView(StaffRequiredMixin, UpdateView):
    """Ubah data pengguna, aktif/nonaktifkan, atau atur ulang kata sandinya."""
    model = User
    form_class = StaffUserUpdateForm
    template_name = "accounts/user_form.html"
    context_object_name = "pengguna"
    success_url = reverse_lazy("user-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['jumlah_buku'] = self.object.recorded_books.count()
        context['diri_sendiri'] = self.object.pk == self.request.user.pk
        return context

    def form_valid(self, form):
        pengguna = form.instance
        # Pengaman: jangan sampai admin menutup aksesnya sendiri
        if pengguna.pk == self.request.user.pk:
            if not form.cleaned_data.get('is_active'):
                messages.error(self.request, 'Anda tidak bisa menonaktifkan akun Anda sendiri.')
                return self.form_invalid(form)
            if not form.cleaned_data.get('is_staff') and not pengguna.is_superuser:
                messages.error(self.request, 'Anda tidak bisa mencabut akses staff milik sendiri.')
                return self.form_invalid(form)

        messages.success(self.request, f'Data pengguna "{pengguna.username}" berhasil diperbarui.')
        ActivityLog.objects.create(
            user=self.request.user, action="UPDATE_USER",
            detail=f"Memperbarui akun: {pengguna.username}",
        )
        return super().form_valid(form)


class UserDeleteView(StaffRequiredMixin, DeleteView):
    """Hapus pengguna. Buku yang pernah ia catat ikut terhapus (relasi CASCADE)."""
    model = User
    template_name = "settings/confirm_delete.html"
    success_url = reverse_lazy("user-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        jumlah = self.object.recorded_books.count()
        context['jenis'] = 'Pengguna'
        context['kembali_url'] = reverse('user-list')
        context['dampak'] = (
            f'{jumlah} buku yang dicatat pengguna ini akan IKUT TERHAPUS. '
            'Bila hanya ingin menonaktifkan, gunakan tombol Ubah lalu hilangkan centang "Akun aktif".'
        )
        return context

    def form_valid(self, form):
        target = self.object
        if target.pk == self.request.user.pk:
            messages.error(self.request, 'Anda tidak bisa menghapus akun Anda sendiri.')
            return redirect('user-list')
        if target.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
            messages.error(self.request, 'Ini satu-satunya akun superuser — tidak boleh dihapus.')
            return redirect('user-list')

        username = target.username
        messages.success(self.request, f'Pengguna "{username}" berhasil dihapus.')
        ActivityLog.objects.create(
            user=self.request.user, action="HAPUS_USER",
            detail=f"Menghapus akun: {username}",
        )
        return super().form_valid(form)


# ─── Identitas aplikasi (judul dinamis) ───────────────────────────────────────

class AppIdentityUpdateView(StaffRequiredMixin, FormView):
    """
    Ubah judul aplikasi / nama singkat / tagline / nama pemilik pada label.
    Hanya admin (staff/superuser) karena berlaku untuk semua pengguna.
    """
    template_name = 'accounts/app_identity_form.html'
    form_class = SiteConfigForm
    success_url = reverse_lazy('settings')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = SiteConfig.get_solo()
        return kwargs

    def form_valid(self, form):
        form.save()
        ActivityLog.objects.create(
            user=self.request.user, action='UPDATE_IDENTITAS',
            detail=f"Mengubah judul aplikasi menjadi: {form.instance.app_name}")
        messages.success(self.request, 'Identitas aplikasi berhasil disimpan.')
        return super().form_valid(form)


# ─── Tambah cepat dari dalam form buku (modal, tanpa pindah halaman) ─────────

class GenreQuickCreateView(LoginRequiredMixin, View):
    """Endpoint JSON: tambah Genre baru langsung dari modal di form buku."""

    def post(self, request):
        form = GenreForm(request.POST)
        if form.is_valid():
            genre = form.save()
            ActivityLog.objects.create(user=request.user, action='TAMBAH_GENRE',
                                       detail=f'Menambahkan genre: {genre.name}')
            return JsonResponse({'ok': True, 'id': genre.pk, 'name': genre.name,
                                 'color': genre.color_code})
        return JsonResponse(
            {'ok': False, 'errors': {f: errs[0] for f, errs in form.errors.items()}},
            status=400)


class ShelfQuickCreateView(LoginRequiredMixin, View):
    """Endpoint JSON: tambah Lokasi Rak baru langsung dari modal di form buku."""

    def post(self, request):
        form = ShelfForm(request.POST)
        if form.is_valid():
            rak = form.save()
            ActivityLog.objects.create(user=request.user, action='TAMBAH_RAK',
                                       detail=f'Menambahkan lokasi rak: {rak.name}')
            return JsonResponse({'ok': True, 'id': rak.pk, 'name': rak.name,
                                 'label': str(rak), 'color': rak.color_code})
        return JsonResponse(
            {'ok': False, 'errors': {f: errs[0] for f, errs in form.errors.items()}},
            status=400)


# ─── Cetak label buku (2 × 3 cm) ─────────────────────────────────────────────

class LabelSelectView(LoginRequiredMixin, ListView):
    """Pilih buku yang akan dicetak labelnya (dengan filter & pencarian)."""
    template_name = 'labels/label_select.html'
    context_object_name = 'books'
    paginate_by = 24

    def get_queryset(self):
        qs = Book.objects.select_related('genre', 'shelf', 'recorded_by').order_by('shelf__name', 'title')
        p = self.request.GET
        if p.get('q'):
            kata = p['q'].strip()
            qs = qs.filter(Q(title__icontains=kata) | Q(author__icontains=kata))
        if p.get('genre'):
            qs = qs.filter(genre_id=p['genre'])
        if p.get('shelf'):
            qs = qs.filter(shelf_id=p['shelf'])
        if p.get('book_type'):
            qs = qs.filter(book_type=p['book_type'])
        if p.get('tanpa_rak') == '1':
            qs = qs.filter(shelf__isnull=True)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genres'] = Genre.objects.order_by('name')
        context['shelves'] = Shelf.objects.order_by('name')
        context['book_types'] = Book.BookCategory.choices
        context['filter'] = self.request.GET
        context['total_hasil'] = self.get_queryset().count()
        # Query string tanpa 'page' untuk tautan paginasi
        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_tanpa_page'] = params.urlencode()
        return context


class LabelPrintView(LoginRequiredMixin, TemplateView):
    """
    Lembar label siap cetak: tiap label 3 × 2 cm (mendatar) atau 2 × 3 cm (tegak).

    Isi label: lokasi rak (menonjol), judul, penulis, dan nama pemilik (opsional).
    Parameter: ?ids=1,2,3  atau  ?semua=1&<filter yang sama dengan LabelSelectView>
    """
    template_name = 'labels/label_print.html'

    def get_queryset(self):
        p = self.request.GET
        ids = [int(x) for x in p.get('ids', '').split(',') if x.strip().isdigit()]
        if ids:
            return (Book.objects.select_related('genre', 'shelf')
                    .filter(pk__in=ids).order_by('shelf__name', 'title'))
        qs = Book.objects.select_related('genre', 'shelf').order_by('shelf__name', 'title')
        if p.get('q'):
            kata = p['q'].strip()
            qs = qs.filter(Q(title__icontains=kata) | Q(author__icontains=kata))
        if p.get('genre'):
            qs = qs.filter(genre_id=p['genre'])
        if p.get('shelf'):
            qs = qs.filter(shelf_id=p['shelf'])
        if p.get('book_type'):
            qs = qs.filter(book_type=p['book_type'])
        if p.get('tanpa_rak') == '1':
            qs = qs.filter(shelf__isnull=True)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['books'] = self.get_queryset()
        # orientasi: 'mendatar' (3×2 cm, default) atau 'tegak' (2×3 cm)
        context['orientasi'] = 'tegak' if self.request.GET.get('orientasi') == 'tegak' else 'mendatar'
        context['mulai_dari'] = self.request.GET.get('mulai', '')     # lompati N label pertama
        # Query string tanpa 'orientasi' — untuk tombol ganti orientasi
        params = self.request.GET.copy()
        params.pop('orientasi', None)
        context['query_tanpa_orientasi'] = params.urlencode()
        return context


# ─── API ──────────────────────────────────────────────────────────────────────

class TitleAutocompleteAPIView(LoginRequiredMixin, View):
    """
    Autocomplete judul buku (field Judul di form perekaman).

    GET /api/titles/?q=<teks>&author=<teks>

    Pencocokan berlapis:
    1. substring pada judul/penulis (case-insensitive, tahan spasi ganda)
    2. fuzzy matching (difflib) terhadap judul unik di DB
    """

    MAX_RESULTS = 8
    FUZZY_POOL = 800

    def get(self, request, *args, **kwargs):
        raw_q = (request.GET.get('q') or '').strip()
        author_q = (request.GET.get('author') or '').strip()
        norm_q = normalize_text(raw_q)

        if len(norm_q) < 2:
            return JsonResponse({'query': raw_q, 'exact_match': False, 'results': []})

        candidates = Book.objects.filter(
            Q(title__icontains=raw_q) | Q(author__icontains=raw_q)
        ).values('title', 'author').annotate(
            count=Count('id'), last_added=Max('created_at')
        ).order_by('-count', 'title')[:50]

        rows = list(candidates)

        pool = list(Book.objects.values_list('title', flat=True).distinct()[:self.FUZZY_POOL])
        norm_pool = {normalize_text(t): t for t in pool}
        close = difflib.get_close_matches(norm_q, list(norm_pool.keys()), n=self.MAX_RESULTS, cutoff=0.72)

        seen = {(normalize_text(r['title']), normalize_text(r['author'])) for r in rows}

        for norm_title in close:
            meta = Book.objects.filter(title_normalized=norm_title).values('title', 'author').annotate(
                count=Count('id'), last_added=Max('created_at')
            ).order_by('-count').first()
            if not meta:
                continue
            key = (normalize_text(meta['title']), normalize_text(meta['author']))
            if key in seen:
                continue
            seen.add(key)
            rows.append(meta)

        results = []
        exact_match = False
        for r in rows:
            sim = difflib.SequenceMatcher(None, norm_q, normalize_text(r['title'])).ratio()
            is_exact = normalize_text(r['title']) == norm_q
            if is_exact:
                exact_match = True

            sample = Book.objects.filter(
                title_normalized=normalize_text(r['title'])
            ).select_related('shelf', 'genre').order_by('-created_at').first()

            results.append({
                'title': r['title'],
                'author': r['author'],
                'count': r['count'],
                'exact': is_exact,
                'similarity': round(sim, 3),
                'shelf': str(sample.shelf) if sample and sample.shelf else '',
                'book_type': sample.get_book_type_display() if sample else '',
                'genre': sample.genre.name if sample and sample.genre else '',
                'url': reverse('book-detail', args=[sample.pk]) if sample else '',
            })

        results.sort(key=lambda x: (not x['exact'], -x['similarity'], -x['count']))
        results = results[:self.MAX_RESULTS]

        return JsonResponse({'query': raw_q, 'exact_match': exact_match, 'results': results})


class StatsAPIView(LoginRequiredMixin, View):
    """API data statistik untuk Chart.js"""

    def get(self, request, *args, **kwargs):
        genre_data = list(Genre.objects.annotate(
            book_count=Count('books')
        ).values('name', 'book_count', 'color_code').order_by('-book_count'))

        from django.db.models.functions import TruncMonth
        monthly = list(Book.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=180)
        ).annotate(month=TruncMonth('created_at')).values('month').annotate(
            count=Count('id')
        ).order_by('month'))

        status_data = list(Book.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count'))

        user_stats = list(User.objects.annotate(
            book_count=Count('recorded_books')
        ).filter(book_count__gt=0).values('username', 'book_count').order_by('-book_count')[:15])

        shelf_data = list(Shelf.objects.annotate(
            book_count=Count('books')
        ).values('name', 'book_count', 'color_code').order_by('-book_count'))

        type_data = [
            {'book_type': label, 'count': Book.objects.filter(book_type=value).count()}
            for value, label in Book.BookCategory.choices
        ]

        return JsonResponse({
            'genre_distribution': genre_data,
            'monthly_additions': monthly,
            'status_distribution': status_data,
            'user_productivity': user_stats,
            'shelf_distribution': shelf_data,
            'book_type_distribution': type_data,
        })


class BookListAPIView(LoginRequiredMixin, View):
    """API datatable buku (JSON)"""

    def get(self, request, *args, **kwargs):
        qs = Book.objects.select_related('genre', 'shelf', 'recorded_by').order_by('-created_at')

        search = request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(author__icontains=search) |
                Q(isbn__icontains=search)
            )

        genre = request.GET.get('genre')
        if genre:
            qs = qs.filter(genre__slug=genre)

        status = request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        user_id = request.GET.get('user')
        if user_id:
            qs = qs.filter(recorded_by_id=user_id)

        shelf_id = request.GET.get('shelf')
        if shelf_id:
            qs = qs.filter(shelf_id=shelf_id)

        book_type = request.GET.get('book_type')
        if book_type:
            qs = qs.filter(book_type=book_type)

        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(page)

        data = {
            'books': [
                {
                    'id': b.id,
                    'title': b.title,
                    'author': b.author,
                    'isbn': b.isbn,
                    'genre': b.genre.name if b.genre else '-',
                    'genre_color': b.genre.color_code if b.genre else '#8A4FFF',
                    'book_type': b.get_book_type_display(),
                    'book_type_color': b.book_type_color,
                    'shelf': str(b.shelf) if b.shelf else '-',
                    'shelf_color': b.shelf.color_code if b.shelf else '#8A4FFF',
                    'status': b.status,
                    'status_display': b.get_status_display(),
                    'recorded_by': b.recorded_by.username,
                    'rating': b.rating,
                    'publication_year': b.publication_year,
                    'purchase_year': b.purchase_year,
                    'created_at': b.created_at.strftime('%d %b %Y %H:%M'),
                    'cover': b.display_cover,
                    'detail_url': b.get_absolute_url(),
                }
                for b in page_obj
            ],
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
        return JsonResponse(data)
