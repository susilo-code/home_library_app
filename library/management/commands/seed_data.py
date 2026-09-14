import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from library.models import ActivityLog, Book, Genre, Shelf, UserProfile, normalize_text

# ── Judul template yang bersifat FIKSI (sisanya Non-Fiksi) ────────────────────
# Dipakai untuk menentukan "Jenis Buku" secara realistis, dan oleh
# `manage.py repair_demo_data` saat memulihkan data demo.
JUDUL_FIKSI = {
    'laskar pelangi', 'bumi manusia', '1984', 'to kill a mockingbird',
    'the great gatsby', 'pride and prejudice', 'the alchemist',
    'negeri 5 menara', 'cantik itu luka',
}


def judul_dasar(judul: str) -> str:
    """Buang penanda edisi, contoh: '1984 (Edisi 3)' -> '1984'."""
    return judul.split(' (Edisi')[0].strip().lower()


class Command(BaseCommand):
    help = "Seed database Home Library (genre, rak buku, jenis buku, user, buku contoh)"

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=5, help='Number of users to create')
        parser.add_argument('--books-per-user', type=int, default=10, help='Books per user')
        parser.add_argument('--clear', action='store_true', help='Clear existing books/activity before seeding')

    def handle(self, *args, **options):
        num_users = options['users']
        books_per_user = options['books_per_user']

        if options['clear']:
            self.stdout.write('Menghapus data buku & aktivitas lama...')
            ActivityLog.objects.all().delete()
            Book.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('  Buku & aktivitas dibersihkan.'))

        # ── 1. GENRE ──────────────────────────────────────────────────────────
        genres_data = [
            {'name': 'Fiksi', 'slug': 'fiksi', 'color_code': '#8A4FFF', 'icon': 'book-open', 'description': 'Novel, cerita pendek, dan karya fiksi lainnya'},
            {'name': 'Non-Fiksi', 'slug': 'non-fiksi', 'color_code': '#06B6D4', 'icon': 'book', 'description': 'Biografi, sejarah, sains, dan pengetahuan umum'},
            {'name': 'Pengembangan Diri', 'slug': 'pengembangan-diri', 'color_code': '#10B981', 'icon': 'lightbulb', 'description': 'Motivasi, produktivitas, psikologi, dan keahlian'},
            {'name': 'Bisnis & Ekonomi', 'slug': 'bisnis-ekonomi', 'color_code': '#F59E0B', 'icon': 'briefcase', 'description': 'Entrepreneurship, keuangan, manajemen, pemasaran'},
            {'name': 'Teknologi', 'slug': 'teknologi', 'color_code': '#6366F1', 'icon': 'cpu', 'description': 'Pemrograman, AI, data science, cybersecurity'},
            {'name': 'Sejarah', 'slug': 'sejarah', 'color_code': '#EC4899', 'icon': 'landmark', 'description': 'Sejarah dunia, Indonesia, peradaban kuno'},
            {'name': 'Sains & Matematika', 'slug': 'sains-matematika', 'color_code': '#14B8A6', 'icon': 'flask-conical', 'description': 'Fisika, kimia, biologi, matematika'},
            {'name': 'Agama & Spiritual', 'slug': 'agama-spiritual', 'color_code': '#F97316', 'icon': 'heart', 'description': 'Kitab suci, teologi, spiritualitas, filsafat'},
            {'name': 'Anak-anak', 'slug': 'anak-anak', 'color_code': '#84CC16', 'icon': 'baby', 'description': 'Buku cerita, pendidikan, dan aktivitas untuk anak'},
            {'name': 'Komik & Graphic Novel', 'slug': 'komik-graphic-novel', 'color_code': '#A855F7', 'icon': 'square-pen', 'description': 'Manga, komik, graphic novel, webtoon'},
        ]
        self.stdout.write('Membuat genre...')
        genres = []
        for g in genres_data:
            obj, created = Genre.objects.get_or_create(slug=g['slug'], defaults=g)
            genres.append(obj)
            if created:
                self.stdout.write(f'  + genre: {obj.name}')

        # ── 2. LOKASI RAK BUKU (dinamis) ──────────────────────────────────────
        shelves_data = [
            {'name': 'Rak A-1 (Kamar Depan)', 'code': 'A1', 'capacity': 60, 'color_code': '#8A4FFF',
             'description': 'Rak kayu utama dekat jendela ruang tamu'},
            {'name': 'Rak A-2 (Kamar Depan)', 'code': 'A2', 'capacity': 60, 'color_code': '#9A6EFF',
             'description': 'Rak kayu sisi kiri, khusus novel & fiksi'},
            {'name': 'Rak B-1 (Kamar Tengah)', 'code': 'B1', 'capacity': 80, 'color_code': '#6366F1',
             'description': 'Rak besi rakitan, koleksi non-fiksi & referensi'},
            {'name': 'Rak B-2 (Kamar Tengah)', 'code': 'B2', 'capacity': 80, 'color_code': '#06B6D4',
             'description': 'Rak besi sisi kanan, buku teknologi & komputer'},
            {'name': 'Lemari Kaca C (Ruang Baca)', 'code': 'C', 'capacity': 40, 'color_code': '#10B981',
             'description': 'Lemari kaca untuk koleksi khusus & buku langka'},
            {'name': 'Rak D (Kamar Belakang)', 'code': 'D', 'capacity': 100, 'color_code': '#F59E0B',
             'description': 'Rak buku anak, komik, dan majalah'},
            {'name': 'Box Penyimpanan E', 'code': 'E', 'capacity': 30, 'color_code': '#EC4899',
             'description': 'Box plastik untuk buku cadangan / belum disortir'},
        ]
        self.stdout.write('Membuat lokasi rak buku...')
        shelves = []
        for s in shelves_data:
            obj, created = Shelf.objects.get_or_create(name=s['name'], defaults=s)
            shelves.append(obj)
            if created:
                self.stdout.write(f'  + rak: {obj.name}')

        # ── 3. JENIS BUKU: tetap 2 pilihan (Fiksi / Non-Fiksi) ────────────────
        # Tidak ada master data lagi — dipakai konstanta Book.BookCategory.
        kategori_genres = [g for g in genres if 'fiksi' in g.slug and 'non' not in g.slug]

        # ── 4. USER ───────────────────────────────────────────────────────────
        self.stdout.write(f'Membuat {num_users} user...')
        users = []
        for i in range(num_users):
            username = f'user{i + 1}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@example.com', 'first_name': 'User', 'last_name': str(i + 1)},
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f'  + user: {username}')

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.bio = f'Halo! Saya {username}, pecinta buku dan pembaca aktif. Genre favorit: {random.choice(genres).name}.'
            profile.phone = f'+62 812-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}'
            profile.theme_preference = random.choice(['dark', 'light'])
            profile.save()
            users.append(user)

        # ── 5. BUKU ───────────────────────────────────────────────────────────
        self.stdout.write(f'Membuat buku ({books_per_user} per user)...')
        book_templates = [
            {'title': 'Laskar Pelangi', 'author': 'Andrea Hirata', 'publisher': 'Bentang Pustaka', 'year': 2005, 'pages': 529, 'isbn': '9789793062795'},
            {'title': 'Bumi Manusia', 'author': 'Pramoedya Ananta Toer', 'publisher': 'Hasta Mitra', 'year': 1980, 'pages': 535, 'isbn': '9789798473016'},
            {'title': 'Atomic Habits', 'author': 'James Clear', 'publisher': 'Gramedia Pustaka Utama', 'year': 2019, 'pages': 352, 'isbn': '9786020633831'},
            {'title': 'The Psychology of Money', 'author': 'Morgan Housel', 'publisher': 'Gramedia Pustaka Utama', 'year': 2021, 'pages': 256, 'isbn': '9786020645674'},
            {'title': 'Sapiens', 'author': 'Yuval Noah Harari', 'publisher': 'Kepustakaan Populer Gramedia', 'year': 2017, 'pages': 512, 'isbn': '9786024249381'},
            {'title': 'Clean Code', 'author': 'Robert C. Martin', 'publisher': 'Pearson', 'year': 2008, 'pages': 464, 'isbn': '9780132350884'},
            {'title': 'Design Patterns', 'author': 'Erich Gamma et al.', 'publisher': 'Addison-Wesley', 'year': 1994, 'pages': 395, 'isbn': '9780201633610'},
            {'title': 'Thinking, Fast and Slow', 'author': 'Daniel Kahneman', 'publisher': 'Farrar, Straus and Giroux', 'year': 2011, 'pages': 499, 'isbn': '9780374533557'},
            {'title': 'The Pragmatic Programmer', 'author': 'Andrew Hunt, David Thomas', 'publisher': 'Addison-Wesley', 'year': 1999, 'pages': 352, 'isbn': '9780201616224'},
            {'title': 'Rich Dad Poor Dad', 'author': 'Robert Kiyosaki', 'publisher': 'Warner Books', 'year': 1997, 'pages': 336, 'isbn': '9781612680194'},
            {'title': '1984', 'author': 'George Orwell', 'publisher': 'Secker & Warburg', 'year': 1949, 'pages': 328, 'isbn': '9780451524935'},
            {'title': 'To Kill a Mockingbird', 'author': 'Harper Lee', 'publisher': 'J.B. Lippincott & Co.', 'year': 1960, 'pages': 281, 'isbn': '9780061120084'},
            {'title': 'The Great Gatsby', 'author': 'F. Scott Fitzgerald', 'publisher': 'Scribner', 'year': 1925, 'pages': 180, 'isbn': '9780743273565'},
            {'title': 'Pride and Prejudice', 'author': 'Jane Austen', 'publisher': 'T. Egerton', 'year': 1813, 'pages': 432, 'isbn': '9780141439518'},
            {'title': 'The Alchemist', 'author': 'Paulo Coelho', 'publisher': 'HarperCollins', 'year': 1988, 'pages': 208, 'isbn': '9780062315007'},
            {'title': 'Filosofi Teras', 'author': 'Henry Manampiring', 'publisher': 'Kompas', 'year': 2018, 'pages': 320, 'isbn': '9786024125189'},
            {'title': 'Negeri 5 Menara', 'author': 'Ahmad Fuadi', 'publisher': 'Gramedia Pustaka Utama', 'year': 2009, 'pages': 423, 'isbn': '9789792248686'},
            {'title': 'Cantik Itu Luka', 'author': 'Eka Kurniawan', 'publisher': 'Gramedia Pustaka Utama', 'year': 2002, 'pages': 520, 'isbn': '9789799686901'},
            {'title': 'Algoritma dan Pemrograman', 'author': 'Rinaldi Munir', 'publisher': 'Informatika', 'year': 2016, 'pages': 412, 'isbn': '9786021516123'},
            {'title': 'Sistem Basis Data', 'author': 'Fathansyah', 'publisher': 'Informatika', 'year': 2015, 'pages': 380, 'isbn': '9786021516017'},
        ]

        statuses = ['UNREAD', 'READING', 'COMPLETED']
        status_weights = [0.4, 0.2, 0.4]
        book_count = 0

        for user in users:
            for _ in range(books_per_user):
                tpl = random.choice(book_templates)
                title = tpl['title']
                # Hindari judul+penulis duplikat untuk user yang sama
                if Book.objects.filter(title_normalized=normalize_text(title),
                                       author_normalized=normalize_text(tpl['author'])).exists():
                    title = f"{title} (Edisi {random.randint(1, 5)})"

                created_at = timezone.now() - timedelta(
                    days=random.randint(0, 180),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )

                genre_buku = random.choice(genres)
                # Jenis buku diturunkan dari sifat judul: fiksi sastra vs non-fiksi
                jenis_buku = (
                    Book.BookCategory.FIKSI
                    if judul_dasar(tpl['title']) in JUDUL_FIKSI
                    else Book.BookCategory.NON_FIKSI
                )
                tahun_terbit = tpl['year']
                tahun_beli = min(
                    timezone.now().year,
                    random.randint(tahun_terbit, timezone.now().year) if tahun_terbit <= timezone.now().year
                    else timezone.now().year,
                )

                book = Book.objects.create(
                    title=title,
                    author=tpl['author'],
                    isbn=tpl['isbn'],
                    genre=genre_buku,
                    shelf=random.choice(shelves),
                    book_type=jenis_buku,
                    recorded_by=user,
                    publication_year=tahun_terbit,
                    purchase_year=tahun_beli,
                    publisher=tpl['publisher'],
                    pages=tpl['pages'],
                    status=random.choices(statuses, weights=status_weights)[0],
                    rating=random.randint(1, 5),
                    summary=(
                        f'Catatan pribadi untuk buku "{title}". '
                        f'{random.choice(["Sangat menginspirasi!", "Wajib dibaca.", "Bagus untuk referensi.", "Membuka wawasan baru.", "Disukai sekali."])}'
                    ),
                    created_at=created_at,
                )

                ActivityLog.objects.create(
                    user=user,
                    action='TAMBAH_BUKU',
                    detail=f'Menambahkan buku: {book.title}',
                    timestamp=created_at,
                )
                book_count += 1

        # ── 6. LENGKAPI BUKU LAMA (rak & tahun beli) ──────────────────────────
        tanpa_rak = Book.objects.filter(shelf__isnull=True)
        n_rak = tanpa_rak.count()
        if n_rak:
            for b in tanpa_rak:
                b.shelf = random.choice(shelves)
                b.save(update_fields=['shelf'])
            self.stdout.write(f'  ~ {n_rak} buku lama diisi lokasi rak acak')

        # Sinkronkan jenis buku HANYA bila genre secara eksplisit Fiksi/Non-Fiksi
        # (tidak menimpa klasifikasi yang sudah diisi manual oleh pengguna)
        tahun_ini = timezone.now().year
        n_sync = 0
        for b in Book.objects.select_related('genre').iterator():
            ubah = []
            if b.genre and b.genre.slug == 'fiksi':
                target = Book.BookCategory.FIKSI
            elif b.genre and b.genre.slug == 'non-fiksi':
                target = Book.BookCategory.NON_FIKSI
            else:
                target = None  # genre lain -> jenis buku dibiarkan apa adanya
            if target and b.book_type != target:
                b.book_type = target
                ubah.append('book_type')
            if not b.purchase_year:
                terbit = b.publication_year or 1900
                b.purchase_year = random.randint(min(terbit, tahun_ini), tahun_ini)
                ubah.append('purchase_year')
            if ubah:
                b.save(update_fields=ubah)
                n_sync += 1
        if n_sync:
            self.stdout.write(f'  ~ {n_sync} buku lama disinkronkan (jenis buku & tahun beli)')

        # Pulihkan genre buku yang kosong (mis. genrenya pernah dihapus)
        genre_fiksi = Genre.objects.filter(slug='fiksi').first()
        genre_non_fiksi = Genre.objects.filter(slug='non-fiksi').first()
        n_genre = 0
        for b in Book.objects.filter(genre__isnull=True):
            if b.book_type == Book.BookCategory.FIKSI and genre_fiksi:
                b.genre = genre_fiksi
            elif b.book_type == Book.BookCategory.NON_FIKSI and genre_non_fiksi:
                b.genre = genre_non_fiksi
            else:
                b.genre = random.choice(genres)
            b.save(update_fields=['genre'])
            n_genre += 1
        if n_genre:
            self.stdout.write(f'  ~ {n_genre} buku tanpa genre dipulihkan')

        # ── RINGKASAN ─────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(f'\nBerhasil membuat {book_count} buku.'))
        self.stdout.write('\n--- RINGKASAN DATABASE ---')
        self.stdout.write(f'User          : {User.objects.count()}')
        self.stdout.write(f'Genre         : {Genre.objects.count()}')
        self.stdout.write(f'Lokasi Rak    : {Shelf.objects.count()}')
        self.stdout.write(f'Jenis Fiksi   : {Book.objects.filter(book_type="FIKSI").count()} buku')
        self.stdout.write(f'Jenis NonFiksi: {Book.objects.filter(book_type="NON_FIKSI").count()} buku')
        self.stdout.write(f'Buku          : {Book.objects.count()}')
        self.stdout.write(f'Activity Log  : {ActivityLog.objects.count()}')
        self.stdout.write('\nLogin default : user1 / password123')
