import re

from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


def normalize_text(value: str) -> str:
    """
    Normalisasi teks untuk perbandingan judul/penulis:
    - rapikan spasi berlebih (termasuk tab/newline) jadi satu spasi
    - hilangkan spasi di ujung
    - casefold (lebih kuat dari lower(), aman untuk Unicode)

    Dipakai agar deteksi duplikat TIDAK peka huruf besar/kecil
    dan tidak bisa dilewati dengan spasi ganda.
    """
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


class UserProfile(models.Model):
    THEME_CHOICES = [
        ('dark', 'Dark Mode'),
        ('light', 'Light Mode'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    theme_preference = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        # Fallback SVG avatar based on username
        return f"https://api.dicebear.com/7.x/initials/svg?seed={self.user.username}&backgroundColor=3b1e54,522b5b&textColor=ffffff"


class Genre(models.Model):
    """
    Genre / Kategori buku — DINAMIS, bisa ditambah/diubah/dihapus dari halaman Pengaturan.
    Contoh: Novel, Sains, Sejarah, Komik, Agama, Teknologi, dsb.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nama Genre / Kategori")
    slug = models.SlugField(max_length=100, unique=True, blank=True, verbose_name="Slug URL")
    description = models.CharField(max_length=255, blank=True, default='', verbose_name="Keterangan")
    color_code = models.CharField(max_length=7, default='#8A4FFF', verbose_name="Warna Label")
    icon = models.CharField(max_length=50, default='bookmark', verbose_name="Ikon")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Genre / Kategori'
        verbose_name_plural = 'Genre / Kategori'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:90] or 'genre'
            slug = base
            n = 1
            while Genre.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f'{base}-{n}'
            self.slug = slug
        super().save(*args, **kwargs)


class Shelf(models.Model):
    """
    Lokasi Rak Buku — DINAMIS, bisa ditambah/diubah/dihapus dari halaman Pengaturan.
    Contoh: "Rak A-1 (Kamar Depan)", "Lemari Kaca B", "Gudang".
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nama Lokasi Rak")
    code = models.CharField(max_length=30, blank=True, default='', verbose_name="Kode Rak",
                            help_text="Kode singkat, contoh: A1, RK-02")
    description = models.CharField(max_length=255, blank=True, default='', verbose_name="Keterangan",
                                   help_text="Contoh: rak kayu dekat jendela, lantai 2")
    color_code = models.CharField(max_length=7, default='#8A4FFF', verbose_name="Warna Label")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Lokasi Rak Buku'
        verbose_name_plural = 'Lokasi Rak Buku'

    def __str__(self):
        return f"{self.name}" + (f" ({self.code})" if self.code else "")


class Book(models.Model):
    class ReadingStatus(models.TextChoices):
        UNREAD = 'UNREAD', 'Belum Dibaca'
        READING = 'READING', 'Sedang Dibaca'
        COMPLETED = 'COMPLETED', 'Selesai Dibaca'

    class BookCategory(models.TextChoices):
        """Jenis buku bersifat TETAP: hanya Fiksi dan Non-Fiksi."""
        FIKSI = 'FIKSI', 'Fiksi'
        NON_FIKSI = 'NON_FIKSI', 'Non-Fiksi'

    title = models.CharField(max_length=255, verbose_name="Judul Buku")
    author = models.CharField(max_length=255, verbose_name="Penulis")
    isbn = models.CharField(max_length=30, blank=True, default='', verbose_name="ISBN")

    # ── Field normalisasi: otomatis diisi di save(), dipakai untuk deteksi duplikat
    #    yang tidak peka huruf besar/kecil maupun spasi berlebih ────────────────
    title_normalized = models.CharField(max_length=255, blank=True, default='', db_index=True, editable=False)
    author_normalized = models.CharField(max_length=255, blank=True, default='', db_index=True, editable=False)

    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, related_name='books',
                              verbose_name="Genre / Kategori")
    book_type = models.CharField(max_length=10, choices=BookCategory.choices,
                                 default=BookCategory.NON_FIKSI, verbose_name="Jenis Buku")
    shelf = models.ForeignKey(Shelf, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='books', verbose_name="Lokasi Rak Buku")
    recorded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recorded_books',
                                    verbose_name="Perekam")

    publication_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="Tahun Terbit")
    purchase_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="Tahun Beli")
    publisher = models.CharField(max_length=255, blank=True, default='', verbose_name="Penerbit")
    pages = models.PositiveIntegerField(null=True, blank=True, verbose_name="Jumlah Halaman")

    status = models.CharField(max_length=15, choices=ReadingStatus.choices,
                              default=ReadingStatus.UNREAD, verbose_name="Status Baca")
    rating = models.PositiveSmallIntegerField(default=5, verbose_name="Rating (1-5)")

    cover_image = models.ImageField(upload_to='book_covers/', null=True, blank=True, verbose_name="Foto Sampul")
    cover_url = models.URLField(max_length=500, blank=True, default='', verbose_name="Cover URL Fallback")
    summary = models.TextField(blank=True, default='', verbose_name="Sinopsis / Catatan")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="Tanggal Input")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Update Terakhir")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.author}"

    def save(self, *args, **kwargs):
        # Selalu sinkronkan versi normalisasi agar deteksi duplikat akurat
        self.title_normalized = normalize_text(self.title)
        self.author_normalized = normalize_text(self.author)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('book-detail', kwargs={'pk': self.pk})

    @property
    def display_cover(self):
        if self.cover_image and hasattr(self.cover_image, 'url'):
            return self.cover_image.url
        if self.cover_url:
            return self.cover_url
        # Fallback book cover illustration
        return f"https://picsum.photos/seed/{self.pk or self.title}/300/420"

    @property
    def shelf_label(self):
        return str(self.shelf) if self.shelf else '—'

    @property
    def book_type_color(self):
        """Warna label untuk jenis buku (Fiksi = ungu, Non-Fiksi = teal)."""
        return '#8A4FFF' if self.book_type == self.BookCategory.FIKSI else '#06B6D4'


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=50)  # e.g., 'TAMBAH_BUKU', 'UPDATE_BUKU', 'HAPUS_BUKU'
    detail = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action} ({self.timestamp:%Y-%m-%d %H:%M})"


class SiteConfig(models.Model):
    """
    Identitas aplikasi — HANYA SATU BARIS (singleton).

    Judul aplikasi dapat diubah dari halaman Pengaturan (menu klik user),
    dan langsung dipakai di judul tab browser, navbar, footer, serta halaman login.
    """
    app_name = models.CharField(
        max_length=150, default="Hirunaza's Library Information System",
        verbose_name="Judul Aplikasi",
        help_text="Tampil di judul tab browser, halaman login, dan footer.")
    app_short_name = models.CharField(
        max_length=80, default="Hirunaza's Library",
        verbose_name="Nama Singkat (navbar)",
        help_text="Dipakai di navbar atas agar ringkas.")
    tagline = models.CharField(
        max_length=160, default="Sistem Informasi Perpustakaan Pribadi",
        verbose_name="Tagline",
        help_text="Teks kecil di bawah judul (halaman login).")
    label_owner = models.CharField(
        max_length=80, blank=True, default='',
        verbose_name="Nama Pemilik (pada label cetak)",
        help_text="Ikut tercetak pada label buku 2×3 cm. Boleh dikosongkan.")
    developer_name = models.CharField(
        max_length=80, default='susilo',
        verbose_name="Nama Pengembang",
        help_text="Tampil pada menu 'Tentang Aplikasi'.")
    repo_url = models.URLField(
        max_length=300, blank=True, default='https://github.com/susilo-code/home_library_app',
        verbose_name="URL Repositori (GitHub)",
        help_text="Tautan kode sumber, ditampilkan pada menu 'Tentang Aplikasi'.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Identitas Aplikasi'
        verbose_name_plural = 'Identitas Aplikasi'

    def __str__(self):
        return self.app_name

    def save(self, *args, **kwargs):
        self.pk = 1                       # paksa selalu satu baris
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> "SiteConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
