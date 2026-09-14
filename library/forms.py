from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q
from datetime import date
import re

from .models import Book, Genre, Shelf, SiteConfig, UserProfile, normalize_text

# ─── Shared CSS classes ───────────────────────────────────────────────────────
INPUT_CLASS = (
    'w-full px-4 py-2.5 border border-purple-200 dark:border-purple-800 rounded-lg '
    'focus:ring-2 focus:ring-purple-500 focus:border-transparent '
    'bg-white dark:bg-purple-950 text-purple-900 dark:text-purple-50 '
    'placeholder-purple-300 dark:placeholder-purple-600 transition-all duration-200'
)
SELECT_CLASS = INPUT_CLASS
TEXTAREA_CLASS = (
    'w-full px-4 py-2.5 border border-purple-200 dark:border-purple-800 rounded-lg '
    'focus:ring-2 focus:ring-purple-500 focus:border-transparent '
    'bg-white dark:bg-purple-950 text-purple-900 dark:text-purple-50 '
    'placeholder-purple-300 dark:placeholder-purple-600 transition-all duration-200 resize-y'
)
FILE_CLASS = (
    'w-full px-4 py-2 border border-purple-200 dark:border-purple-800 rounded-lg '
    'focus:ring-2 focus:ring-purple-500 focus:border-transparent '
    'bg-white dark:bg-purple-950 text-purple-900 dark:text-purple-50 '
    'file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 '
    'file:text-sm file:font-semibold file:bg-purple-100 dark:file:bg-purple-900 '
    'file:text-purple-700 dark:file:text-purple-200 '
    'hover:file:bg-purple-200 dark:hover:file:bg-purple-800 transition-all duration-200'
)


def re_collapse(value: str) -> str:
    """Rapikan spasi ganda/tab/newline pada input judul & penulis (tetap pertahankan kapitalisasi)."""
    return re.sub(r'\s+', ' ', (value or '').strip())


class BookForm(forms.ModelForm):
    """
    Form perekaman buku — Hirunaza's Library Information System.

    Field WAJIB (selalu terlihat):
    • title      – Judul Buku        • author  – Nama Penulis
    • book_type  – Jenis Buku (Fiksi / Non-Fiksi, pilihan TETAP)
    • genre      – Genre / Kategori (DINAMIS dari Pengaturan)
    • shelf      – Lokasi Rak Buku (DINAMIS dari Pengaturan)
    • status     – Status Baca

    Field OPSIONAL (disembunyikan default, buka bila perlu):
    • isbn, publication_year, purchase_year (Tahun Beli), publisher, pages,
      rating, cover_image, cover_url, summary

    Validasi:
    • Duplikat judul+penulis TIDAK peka huruf besar/kecil & spasi ganda.
    • ISBN hanya angka & '-', 10 atau 13 digit.
    • Tahun terbit & tahun beli tidak melebihi tahun sekarang.
    """

    class Meta:
        model = Book
        fields = [
            'title', 'author', 'isbn', 'book_type', 'genre', 'shelf',
            'publication_year', 'purchase_year', 'publisher', 'pages',
            'status', 'rating',
            'cover_image', 'cover_url',
            'summary',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Ketik judul buku… saran judul mirip akan muncul otomatis',
                'autocomplete': 'off',
                'id': 'id_title',
            }),
            'author': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Contoh: Andrea Hirata',
                'autocomplete': 'off',
                'id': 'id_author',
            }),
            'isbn': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Contoh: 978-979-3062-79-5',
                'maxlength': '20',
            }),
            # Jenis buku: pilihan tetap (Fiksi / Non-Fiksi)
            'book_type': forms.Select(attrs={'class': SELECT_CLASS}),
            'genre': forms.Select(attrs={'class': SELECT_CLASS}),
            'shelf': forms.Select(attrs={'class': SELECT_CLASS}),
            'publication_year': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': f'Contoh: 2005',
                'min': 1000,
                'max': date.today().year,
            }),
            'purchase_year': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': f'Contoh: {date.today().year}',
                'min': 1900,
                'max': date.today().year,
            }),
            'publisher': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Contoh: Bentang Pustaka',
            }),
            'pages': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Contoh: 529',
                'min': 1,
            }),
            'status': forms.Select(attrs={'class': SELECT_CLASS}),
            'rating': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'min': 1, 'max': 5, 'step': 1,
            }),
            'cover_image': forms.ClearableFileInput(attrs={
                'class': FILE_CLASS,
                'accept': 'image/jpeg,image/png,image/webp,image/gif',
            }),
            'cover_url': forms.URLInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'https://example.com/cover.jpg',
            }),
            'summary': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 4,
                'placeholder': 'Sinopsis, catatan pribadi, atau kesan setelah membaca buku ini...',
            }),
        }
        labels = {
            'title': 'Judul Buku',
            'author': 'Penulis',
            'isbn': 'ISBN',
            'book_type': 'Jenis Buku',
            'genre': 'Genre / Kategori',
            'shelf': 'Lokasi Rak Buku',
            'publication_year': 'Tahun Terbit',
            'purchase_year': 'Tahun Beli',
            'publisher': 'Penerbit',
            'pages': 'Jumlah Halaman',
            'status': 'Status Baca',
            'rating': 'Rating (1–5)',
            'cover_image': 'Upload Foto Sampul',
            'cover_url': 'Atau URL Foto Sampul',
            'summary': 'Sinopsis / Catatan Pribadi',
        }
        help_texts = {
            'isbn': 'Format: ISBN-10 (10 digit) atau ISBN-13 (13 digit), tanda "-" diperbolehkan.',
            'book_type': 'Pilihan tetap: Fiksi atau Non-Fiksi.',
            'genre': 'Kelola daftar genre di halaman Pengaturan.',
            'shelf': 'Kelola daftar rak di halaman Pengaturan.',
            'rating': '1 = Sangat Buruk  ·  2 = Buruk  ·  3 = Cukup  ·  4 = Bagus  ·  5 = Luar Biasa',
            'cover_image': 'Format: JPG, PNG, WEBP, GIF · Maksimal 5MB.',
            'cover_url': 'Isi salah satu: upload file atau URL gambar.',
            'publication_year': f'Tahun 1000 s.d. {date.today().year}.',
            'purchase_year': f'Tahun 1900 s.d. {date.today().year}.',
        }
        error_messages = {
            'title': {'required': 'Judul buku wajib diisi.'},
            'author': {'required': 'Nama penulis wajib diisi.'},
            'book_type': {'required': 'Pilih jenis buku (Fiksi / Non-Fiksi).'},
            'genre': {'required': 'Pilih genre / kategori buku.'},
            'status': {'required': 'Pilih status baca buku.'},
        }

    # Diisi oleh clean() bila judul+penulis sudah pernah diinput
    duplicate_warning = None
    duplicate_matches = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in ['title', 'author', 'book_type', 'genre', 'status']:
            self.fields[field_name].label = f'{self.fields[field_name].label} *'

        self._limit_dynamic_choices()

        self.fields['rating'].required = True
        self.fields['rating'].validators = [
            MinValueValidator(1, 'Rating minimal 1 bintang.'),
            MaxValueValidator(5, 'Rating maksimal 5 bintang.'),
        ]

        # Genre & rak opsional secara struktur, tapi sangat disarankan
        for name, label in (('genre', 'Genre / Kategori'), ('shelf', 'Lokasi Rak Buku')):
            self.fields[name].empty_label = f'— Pilih {label} —'

    def _limit_dynamic_choices(self):
        """Dropdown genre & rak hanya menampilkan data AKTIF + nilai yang sedang dipakai (mode edit)."""
        current_genre = getattr(self.instance, 'genre_id', None)
        current_shelf = getattr(self.instance, 'shelf_id', None)

        genres = Genre.objects.filter(Q(is_active=True) | Q(pk=current_genre)) if current_genre \
            else Genre.objects.filter(is_active=True)
        shelves = Shelf.objects.filter(Q(is_active=True) | Q(pk=current_shelf)) if current_shelf \
            else Shelf.objects.filter(is_active=True)
        self.fields['genre'].queryset = genres
        self.fields['shelf'].queryset = shelves

    # ── Validasi per-field ───────────────────────────────────────────────────

    def clean_title(self):
        title = re_collapse(self.cleaned_data.get('title', ''))
        if not title:
            raise forms.ValidationError('Judul buku wajib diisi.')
        if len(title) < 2:
            raise forms.ValidationError('Judul buku terlalu pendek (minimal 2 karakter).')
        if len(title) > 255:
            raise forms.ValidationError('Judul buku terlalu panjang (maksimal 255 karakter).')
        return title

    def clean_author(self):
        author = re_collapse(self.cleaned_data.get('author', ''))
        if not author:
            raise forms.ValidationError('Nama penulis wajib diisi.')
        if len(author) < 2:
            raise forms.ValidationError('Nama penulis terlalu pendek (minimal 2 karakter).')
        if len(author) > 255:
            raise forms.ValidationError('Nama penulis terlalu panjang (maksimal 255 karakter).')
        return author

    def clean_isbn(self):
        isbn = self.cleaned_data.get('isbn', '').strip()
        if not isbn:
            return isbn
        isbn_digits = isbn.replace('-', '').replace(' ', '')
        if not isbn_digits.isdigit():
            raise forms.ValidationError('ISBN hanya boleh berisi angka dan tanda "-".')
        if len(isbn_digits) not in (10, 13):
            raise forms.ValidationError(
                f'ISBN harus 10 digit (ISBN-10) atau 13 digit (ISBN-13). '
                f'Yang dimasukkan: {len(isbn_digits)} digit.'
            )
        return isbn

    def clean_publication_year(self):
        year = self.cleaned_data.get('publication_year')
        if year is None:
            return year
        current_year = date.today().year
        if year < 1000:
            raise forms.ValidationError('Tahun terbit tidak valid (minimal tahun 1000).')
        if year > current_year:
            raise forms.ValidationError(
                f'Tahun terbit tidak boleh melebihi tahun sekarang ({current_year}).'
            )
        return year

    def clean_purchase_year(self):
        year = self.cleaned_data.get('purchase_year')
        if year is None:
            return year
        current_year = date.today().year
        if year < 1900:
            raise forms.ValidationError('Tahun beli tidak valid (minimal tahun 1900).')
        if year > current_year:
            raise forms.ValidationError(
                f'Tahun beli tidak boleh melebihi tahun sekarang ({current_year}).'
            )
        # Tahun beli tidak boleh lebih awal dari tahun terbit
        terbit = self.cleaned_data.get('publication_year')
        if terbit and year < terbit:
            raise forms.ValidationError(
                f'Tahun beli ({year}) tidak boleh lebih awal dari tahun terbit ({terbit}).'
            )
        return year

    def clean_pages(self):
        pages = self.cleaned_data.get('pages')
        if pages is None:
            return pages
        if pages < 1:
            raise forms.ValidationError('Jumlah halaman minimal 1.')
        if pages > 99999:
            raise forms.ValidationError('Jumlah halaman tidak masuk akal (>99.999). Periksa kembali.')
        return pages

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is None:
            raise forms.ValidationError('Rating wajib diisi (1–5).')
        if not (1 <= rating <= 5):
            raise forms.ValidationError('Rating harus antara 1 sampai 5.')
        return rating

    def clean_cover_image(self):
        image = self.cleaned_data.get('cover_image')
        if not image:
            return image
        if hasattr(image, 'size'):
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    f'Ukuran file terlalu besar ({image.size // 1024 // 1024}MB). Maksimal 5MB.'
                )
            allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise forms.ValidationError('Format gambar tidak didukung. Gunakan JPG, PNG, WEBP, atau GIF.')
        return image

    # ── Validasi antar-field ─────────────────────────────────────────────────

    def clean(self):
        cleaned_data = super().clean()
        title = (cleaned_data.get('title') or '').strip()
        author = (cleaned_data.get('author') or '').strip()

        if title and author:
            # Bandingkan versi NORMALISASI (tanpa pengaruh huruf besar/kecil & spasi ganda)
            norm_title = normalize_text(title)
            norm_author = normalize_text(author)

            qs = Book.objects.filter(
                title_normalized=norm_title,
                author_normalized=norm_author,
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            matches = list(qs.select_related('recorded_by', 'shelf', 'genre')[:5])
            if matches:
                self.duplicate_matches = matches
                lines = []
                for b in matches[:3]:
                    rak = f" · rak: {b.shelf}" if b.shelf else ''
                    lines.append(
                        f'"{b.title}" oleh {b.author} — dicatat {b.recorded_by.username} '
                        f'pada {b.created_at.strftime("%d %b %Y")}{rak}'
                    )
                sisa = f' (dan {len(matches) - 3} lainnya)' if len(matches) > 3 else ''
                self.duplicate_warning = (
                    'Buku ini kemungkinan sudah pernah diinput — pencocokan mengabaikan '
                    'huruf besar/kecil dan spasi berlebih: ' + ' | '.join(lines) + sisa + '. '
                    'Tekan "Tetap Simpan" jika ini memang edisi/versi berbeda.'
                )

        # Jangan simpan file DAN URL sekaligus
        cover_image = cleaned_data.get('cover_image')
        cover_url = cleaned_data.get('cover_url')
        if cover_image and hasattr(cover_image, 'size') and cover_url:
            cleaned_data['cover_url'] = ''

        return cleaned_data


# ─── Profil ───────────────────────────────────────────────────────────────────

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio', 'phone']
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={
                'class': FILE_CLASS,
                'accept': 'image/jpeg,image/png,image/webp',
            }),
            'bio': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'rows': 4,
                'placeholder': 'Ceritakan tentang dirimu, genre favorit, atau hobi membaca...',
                'maxlength': '500',
            }),
            'phone': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Contoh: +62 812-3456-7890',
                'maxlength': '20',
            }),
        }
        labels = {
            'avatar': 'Foto Profil',
            'bio': 'Bio / Tentang Saya',
            'phone': 'Nomor Telepon',
        }
        help_texts = {
            'bio': 'Maksimal 500 karakter.',
            'avatar': 'Format: JPG, PNG, WEBP · Maksimal 2MB.',
            'phone': 'Format bebas. Contoh: +62 812-3456-7890',
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if not avatar:
            return avatar
        if hasattr(avatar, 'size'):
            if avatar.size > 2 * 1024 * 1024:
                raise forms.ValidationError(
                    f'Ukuran foto terlalu besar ({avatar.size // 1024}KB). Maksimal 2MB.'
                )
            allowed_types = ['image/jpeg', 'image/png', 'image/webp']
            if hasattr(avatar, 'content_type') and avatar.content_type not in allowed_types:
                raise forms.ValidationError('Format gambar tidak didukung. Gunakan JPG, PNG, atau WEBP.')
        return avatar

    def clean_bio(self):
        bio = self.cleaned_data.get('bio', '').strip()
        if len(bio) > 500:
            raise forms.ValidationError('Bio terlalu panjang. Maksimal 500 karakter.')
        return bio

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            return phone
        digits_only = ''.join(filter(str.isdigit, phone))
        if len(digits_only) < 8:
            raise forms.ValidationError('Nomor telepon terlalu pendek (minimal 8 digit).')
        if len(digits_only) > 15:
            raise forms.ValidationError('Nomor telepon terlalu panjang (maksimal 15 digit).')
        return phone


# ─── Pengaturan akun ──────────────────────────────────────────────────────────

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['theme_preference']
        widgets = {
            'theme_preference': forms.RadioSelect(attrs={'class': 'space-y-2'}),
        }
        labels = {
            'theme_preference': 'Preferensi Tema',
        }


# ─── Autentikasi (form login ber-styling) ─────────────────────────────────────

LOGIN_INPUT_CLASS = (
    'w-full px-4 py-3 pl-11 border border-purple-400/30 rounded-xl '
    'bg-white/5 text-white placeholder-purple-200/50 '
    'focus:ring-2 focus:ring-purple-400 focus:border-transparent '
    'transition-all duration-200 autofill-none'
)


class StyledAuthenticationForm(AuthenticationForm):
    """Form login dengan widget ber-styling khusus tema ungu tua halaman login."""

    username = forms.CharField(
        label="Nama Pengguna",
        widget=forms.TextInput(attrs={
            'class': LOGIN_INPUT_CLASS,
            'placeholder': 'Masukkan nama pengguna',
            'autofocus': True,
            'autocapitalize': 'none',
            'autocomplete': 'username',
            'id': 'id_username',
        }),
    )
    password = forms.CharField(
        label="Kata Sandi",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': LOGIN_INPUT_CLASS,
            'placeholder': 'Masukkan kata sandi',
            'autocomplete': 'current-password',
            'id': 'id_password',
        }),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Nama pengguna atau kata sandi salah. Periksa kembali (perhatikan huruf besar/kecil).',
        'inactive': 'Akun ini tidak aktif. Hubungi administrator.',
    }


# ─── Manajemen pengguna (khusus admin/staff) ──────────────────────────────────

class StaffUserCreateForm(forms.ModelForm):
    """Tambah pengguna baru dari dalam aplikasi (tanpa perlu panel admin Django)."""

    password1 = forms.CharField(
        label="Kata Sandi",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': INPUT_CLASS, 'autocomplete': 'new-password',
                                          'placeholder': 'Minimal 8 karakter'}),
        help_text="Minimal 8 karakter, jangan terlalu umum, dan tidak mirip nama pengguna.",
    )
    password2 = forms.CharField(
        label="Ulangi Kata Sandi",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': INPUT_CLASS, 'autocomplete': 'new-password',
                                          'placeholder': 'Ulangi kata sandi'}),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Contoh: hirunaza',
                                               'autocomplete': 'off'}),
            'first_name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nama depan'}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nama belakang'}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'nama@email.com'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-purple-300 text-purple-600 focus:ring-purple-500'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-purple-300 text-purple-600 focus:ring-purple-500'}),
        }
        labels = {
            'username': 'Nama Pengguna (untuk login)',
            'first_name': 'Nama Depan',
            'last_name': 'Nama Belakang',
            'email': 'Email',
            'is_staff': 'Beri akses panel admin (staff)',
            'is_active': 'Akun aktif (bisa login)',
        }
        help_texts = {
            'username': 'Hanya huruf, angka, dan @ . + - _',
            'is_staff': 'Staff dapat mengelola pengguna, genre, dan rak.',
            'is_active': 'Hilangkan centang untuk menonaktifkan tanpa menghapus.',
        }

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if len(username) < 3:
            raise forms.ValidationError('Nama pengguna minimal 3 karakter.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Nama pengguna ini sudah dipakai.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email ini sudah dipakai akun lain.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Kata sandi dan ulangannya tidak sama.')
        # Catatan: kata sandi sengaja DIBEBASKAN — tidak ada aturan panjang/kerumitan.
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class StaffUserUpdateForm(forms.ModelForm):
    """Ubah data pengguna; kata sandi boleh dikosongkan (tidak diubah)."""

    password_baru = forms.CharField(
        label="Kata Sandi Baru (opsional)",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={'class': INPUT_CLASS, 'autocomplete': 'new-password',
                                          'placeholder': 'Kosongkan bila tidak diubah'}),
        help_text="Isi hanya bila ingin mengganti kata sandi pengguna ini.",
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_staff', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-purple-300 text-purple-600 focus:ring-purple-500'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-purple-300 text-purple-600 focus:ring-purple-500'}),
        }

    def clean_password_baru(self):
        # Kata sandi dibebaskan: tidak ada validasi panjang maupun kerumitan.
        return self.cleaned_data.get('password_baru')

    def save(self, commit=True):
        user = super().save(commit=False)
        sandi = self.cleaned_data.get('password_baru')
        if sandi:
            user.set_password(sandi)
        if commit:
            user.save()
        return user


# ─── Master data dinamis: Genre / Kategori ────────────────────────────────────

class GenreForm(forms.ModelForm):
    class Meta:
        model = Genre
        fields = ['name', 'description', 'color_code', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Contoh: Novel, Sains, Sejarah'}),
            'description': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Contoh: novel & cerita panjang'}),
            'color_code': forms.TextInput(attrs={'class': INPUT_CLASS, 'type': 'color'}),
            'icon': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'bookmark'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-purple-300 text-purple-600 focus:ring-purple-500'}),
        }
        labels = {
            'name': 'Nama Genre / Kategori',
            'description': 'Keterangan',
            'color_code': 'Warna Label',
            'icon': 'Nama Ikon',
            'is_active': 'Aktif (tampil di form perekaman)',
        }
        help_texts = {
            'icon': 'Nama ikon Lucide, contoh: bookmark, book, flask-conical.',
        }
        error_messages = {
            'name': {'required': 'Nama genre / kategori wajib diisi.'},
        }

    def clean_name(self):
        name = re_collapse(self.cleaned_data.get('name', ''))
        if len(name) < 2:
            raise forms.ValidationError('Nama genre minimal 2 karakter.')
        qs = Genre.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Genre dengan nama ini sudah ada.')
        return name

    def clean_color_code(self):
        color = (self.cleaned_data.get('color_code') or '').strip()
        if not color:
            return '#8A4FFF'
        if not color.startswith('#') or len(color) not in (4, 7):
            raise forms.ValidationError('Warna harus format hex, contoh: #8A4FFF.')
        return color


# ─── Master data dinamis: Lokasi Rak Buku ─────────────────────────────────────

class ShelfForm(forms.ModelForm):
    class Meta:
        model = Shelf
        fields = ['name', 'code', 'description', 'color_code', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Contoh: Rak A-1 (Kamar Depan)'}),
            'code': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Contoh: A1'}),
            'description': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Contoh: rak kayu dekat jendela'}),
            'color_code': forms.TextInput(attrs={'class': INPUT_CLASS, 'type': 'color'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 rounded border-purple-300 text-purple-600 focus:ring-purple-500'}),
        }
        labels = {
            'name': 'Nama Lokasi Rak',
            'code': 'Kode Rak',
            'description': 'Keterangan',
            'color_code': 'Warna Label',
            'is_active': 'Aktif (tampil di form perekaman)',
        }
        error_messages = {
            'name': {'required': 'Nama lokasi rak wajib diisi.'},
        }

    def clean_name(self):
        name = re_collapse(self.cleaned_data.get('name', ''))
        if len(name) < 2:
            raise forms.ValidationError('Nama lokasi rak minimal 2 karakter.')
        qs = Shelf.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Lokasi rak dengan nama ini sudah ada.')
        return name

    def clean_color_code(self):
        color = (self.cleaned_data.get('color_code') or '').strip()
        if not color:
            return '#8A4FFF'
        if not color.startswith('#') or len(color) not in (4, 7):
            raise forms.ValidationError('Warna harus format hex, contoh: #8A4FFF.')
        return color


# ─── Master data dinamis: Identitas Aplikasi (judul bisa disetting) ──────────

class SiteConfigForm(forms.ModelForm):
    """Form untuk mengubah judul/nama singkat/tagline aplikasi dari Pengaturan."""

    class Meta:
        model = SiteConfig
        fields = ['app_name', 'app_short_name', 'tagline', 'label_owner', 'developer_name', 'repo_url']
        widgets = {
            'app_name': forms.TextInput(attrs={
                'class': INPUT_CLASS, 'maxlength': 150,
                'placeholder': "Contoh: Hirunaza's Library Information System"}),
            'app_short_name': forms.TextInput(attrs={
                'class': INPUT_CLASS, 'maxlength': 80,
                'placeholder': "Contoh: Hirunaza's Library"}),
            'tagline': forms.TextInput(attrs={
                'class': INPUT_CLASS, 'maxlength': 160,
                'placeholder': 'Contoh: Sistem Informasi Perpustakaan Pribadi'}),
            'label_owner': forms.TextInput(attrs={
                'class': INPUT_CLASS, 'maxlength': 80,
                'placeholder': 'Contoh: Keluarga Hirunaza (boleh dikosongkan)'}),
            'developer_name': forms.TextInput(attrs={
                'class': INPUT_CLASS, 'maxlength': 80,
                'placeholder': 'Contoh: susilo'}),
            'repo_url': forms.URLInput(attrs={
                'class': INPUT_CLASS, 'maxlength': 300,
                'placeholder': 'https://github.com/susilo-code/home_library_app'}),
        }
        labels = {
            'app_name': 'Judul Aplikasi',
            'app_short_name': 'Nama Singkat (navbar)',
            'tagline': 'Tagline',
            'label_owner': 'Nama Pemilik (pada label cetak)',
            'developer_name': 'Nama Pengembang',
            'repo_url': 'URL Repositori (GitHub)',
        }
        error_messages = {
            'app_name': {'required': 'Judul aplikasi wajib diisi.'},
            'app_short_name': {'required': 'Nama singkat wajib diisi.'},
        }
