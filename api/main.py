"""
Service FastAPI — Hirunaza's Library Information System

Berjalan terpisah dari Django (port berbeda) dan membaca database yang SAMA
lewat Django ORM. Cocok untuk konsumsi data oleh aplikasi/mobile lain.

Menjalankan manual:
    .venv\\Scripts\\python.exe -m uvicorn api.main:app --reload --port 8001
Atau gunakan start.bat (Django + FastAPI sekaligus).
"""
import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import List, Optional

import django

# ── Bootstrap Django (harus sebelum import model) ─────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dotenv import load_dotenv  # noqa: E402
from django.core.paginator import Paginator  # noqa: E402
from django.db.models import Count, Q  # noqa: E402
from django.db.models.functions import TruncMonth  # noqa: E402
from django.utils import timezone  # noqa: E402
from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from library.models import ActivityLog, Book, Genre, Shelf, User  # noqa: E402

load_dotenv(BASE_DIR / '.env')


app = FastAPI(
    title="Hirunaza's Library API",
    description="API data perpustakaan rumah (Dashboard, Buku, Genre, Rak, Aktivitas)",
    version="1.2.0",
)

# CORS: untuk pengembangan lokal. Batasi daftar origin bila sudah dipakai publik.
_origins = os.getenv('CORS_ALLOW_ORIGINS', '*')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'] if _origins.strip() == '*' else [o.strip() for o in _origins.split(',')],
    allow_credentials=False if _origins.strip() == '*' else True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# ─── Skema response ───────────────────────────────────────────────────────────
class GenreStat(BaseModel):
    name: str
    book_count: int
    color_code: str


class MonthlyStat(BaseModel):
    month: str
    count: int


class StatusStat(BaseModel):
    status: str
    count: int


class UserStat(BaseModel):
    username: str
    book_count: int


class DashboardStats(BaseModel):
    genre_distribution: List[GenreStat]
    monthly_additions: List[MonthlyStat]
    status_distribution: List[StatusStat]
    user_productivity: List[UserStat]
    shelf_distribution: List[GenreStat]
    book_type_distribution: List[dict]
    total_books: int
    total_genres: int
    total_users: int


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    genre: str
    genre_color: str
    book_type: str            # Fiksi / Non-Fiksi
    book_type_code: str       # FIKSI / NON_FIKSI
    shelf: str
    publication_year: Optional[int] = None
    purchase_year: Optional[int] = None
    status: str
    status_display: str
    recorded_by: str
    rating: int
    created_at: str
    cover: str
    detail_url: str


class PaginatedBooks(BaseModel):
    books: List[BookResponse]
    pagination: dict


def serialize_book(b: Book) -> dict:
    return {
        "id": b.id,
        "title": b.title,
        "author": b.author,
        "isbn": b.isbn,
        "genre": b.genre.name if b.genre else "-",
        "genre_color": b.genre.color_code if b.genre else "#8A4FFF",
        "book_type": b.get_book_type_display(),
        "book_type_code": b.book_type,
        "shelf": str(b.shelf) if b.shelf else "-",
        "publication_year": b.publication_year,
        "purchase_year": b.purchase_year,
        "status": b.status,
        "status_display": b.get_status_display(),
        "recorded_by": b.recorded_by.username,
        "rating": b.rating,
        "created_at": b.created_at.strftime('%d %b %Y %H:%M'),
        "cover": b.display_cover,
        "detail_url": f"/buku/{b.pk}/",
    }


# ─── Endpoint ─────────────────────────────────────────────────────────────────
# CATATAN PENTING:
# Semua endpoint sengaja memakai `def` (SINKRON), bukan `async def`.
# Django ORM bersifat sinkron — bila dipanggil dari konteks async akan error
# "SynchronousOnlyOperation: You cannot call this from an async context".
# Dengan `def` biasa, FastAPI otomatis menjalankannya di threadpool sehingga
# query database aman dan tetap non-blocking bagi event loop.

@app.get("/")
def root():
    return {
        "message": "Hirunaza's Library API",
        "version": "1.2.0",
        "docs": "/docs",
        "endpoints": ["/api/stats", "/api/books", "/api/books/{id}", "/api/genres",
                      "/api/shelves", "/api/users", "/api/activities"],
    }


@app.get("/api/health")
def health():
    """Cek kesiapan service + koneksi database."""
    return {
        "status": "ok",
        "database": "connected",
        "total_books": Book.objects.count(),
        "total_genres": Genre.objects.count(),
        "total_shelves": Shelf.objects.count(),
    }


@app.get("/api/stats", response_model=DashboardStats)
def get_dashboard_stats():
    """Statistik untuk grafik dashboard."""
    genre_data = list(Genre.objects.annotate(
        book_count=Count('books')
    ).values('name', 'book_count', 'color_code').order_by('-book_count'))

    monthly = list(Book.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=180)
    ).annotate(month=TruncMonth('created_at')).values('month').annotate(
        count=Count('id')
    ).order_by('month'))
    monthly_formatted = [
        {"month": item['month'].strftime('%Y-%m'), "count": item['count']}
        for item in monthly
    ]

    status_data = list(Book.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count'))

    user_stats = list(User.objects.annotate(
        book_count=Count('recorded_books')
    ).filter(book_count__gt=0).values('username', 'book_count').order_by('-book_count')[:15])

    shelf_data = list(Shelf.objects.annotate(
        book_count=Count('books')
    ).values('name', 'book_count', 'color_code').order_by('-book_count'))

    book_type_data = [
        {"book_type": label, "book_type_code": value,
         "count": Book.objects.filter(book_type=value).count()}
        for value, label in Book.BookCategory.choices
    ]

    return {
        "genre_distribution": genre_data,
        "monthly_additions": monthly_formatted,
        "status_distribution": status_data,
        "user_productivity": user_stats,
        "shelf_distribution": shelf_data,
        "book_type_distribution": book_type_data,
        "total_books": Book.objects.count(),
        "total_genres": Genre.objects.count(),
        "total_users": User.objects.filter(recorded_books__isnull=False).distinct().count(),
    }


@app.get("/api/books", response_model=PaginatedBooks)
def get_books(
    q: Optional[str] = None,
    genre: Optional[str] = None,
    book_type: Optional[str] = None,
    shelf: Optional[int] = None,
    status: Optional[str] = None,
    user: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
):
    """Daftar buku dengan pencarian, filter, dan paginasi."""
    qs = Book.objects.select_related('genre', 'shelf', 'recorded_by').order_by('-created_at')

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(author__icontains=q) | Q(isbn__icontains=q))
    if genre:
        qs = qs.filter(genre__slug=genre)
    if book_type:
        qs = qs.filter(book_type=book_type.upper())
    if shelf:
        qs = qs.filter(shelf_id=shelf)
    if status:
        qs = qs.filter(status=status.upper())
    if user:
        qs = qs.filter(recorded_by_id=user)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)

    return {
        "books": [serialize_book(b) for b in page_obj],
        "pagination": {
            "current_page": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_items": paginator.count,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        },
    }


@app.get("/api/books/{book_id}")
def get_book(book_id: int):
    """Detail satu buku."""
    try:
        book = Book.objects.select_related(
            'genre', 'shelf', 'recorded_by', 'recorded_by__profile'
        ).get(pk=book_id)
    except Book.DoesNotExist:
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")

    data = serialize_book(book)
    data.update({
        "publisher": book.publisher,
        "pages": book.pages,
        "summary": book.summary,
        "shelf_code": book.shelf.code if book.shelf else "",
        "recorded_by_detail": {
            "id": book.recorded_by.id,
            "username": book.recorded_by.username,
            "avatar": book.recorded_by.profile.avatar_url,
        },
        "created_at_iso": book.created_at.isoformat(),
        "updated_at": book.updated_at.isoformat(),
    })
    return data


@app.get("/api/genres")
def get_genres(aktif_saja: bool = False):
    """Daftar genre/kategori (dinamis) beserta jumlah buku."""
    qs = Genre.objects.annotate(book_count=Count('books')).order_by('name')
    if aktif_saja:
        qs = qs.filter(is_active=True)
    return [
        {
            "id": g.id,
            "name": g.name,
            "slug": g.slug,
            "description": g.description,
            "color_code": g.color_code,
            "icon": g.icon,
            "is_active": g.is_active,
            "book_count": g.book_count,
        }
        for g in qs
    ]


@app.get("/api/shelves")
def get_shelves(aktif_saja: bool = False):
    """Daftar lokasi rak buku (dinamis) beserta jumlah buku."""
    qs = Shelf.objects.annotate(book_count=Count('books')).order_by('name')
    if aktif_saja:
        qs = qs.filter(is_active=True)
    return [
        {
            "id": s.id,
            "name": s.name,
            "code": s.code,
            "description": s.description,
            "capacity": s.capacity,
            "color_code": s.color_code,
            "is_active": s.is_active,
            "book_count": s.book_count,
            "fill_percent": s.fill_percent,
        }
        for s in qs
    ]


@app.get("/api/book-types")
def get_book_types():
    """Jenis buku bersifat tetap: Fiksi & Non-Fiksi."""
    return [
        {
            "code": value,
            "label": label,
            "count": Book.objects.filter(book_type=value).count(),
        }
        for value, label in Book.BookCategory.choices
    ]


@app.get("/api/users")
def get_users():
    """Daftar kontributor beserta jumlah buku yang dicatat."""
    users = User.objects.annotate(
        book_count=Count('recorded_books')
    ).filter(book_count__gt=0).order_by('-book_count')
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "book_count": u.book_count,
            "avatar": u.profile.avatar_url if hasattr(u, 'profile') else None,
        }
        for u in users
    ]


@app.get("/api/activities")
def get_activities(limit: int = Query(20, ge=1, le=100)):
    """Aktivitas perekaman terbaru."""
    activities = ActivityLog.objects.select_related('user', 'user__profile').order_by('-timestamp')[:limit]
    return [
        {
            "id": a.id,
            "user": a.user.username,
            "user_avatar": a.user.profile.avatar_url,
            "action": a.action,
            "detail": a.detail,
            "timestamp": a.timestamp.isoformat(),
        }
        for a in activities
    ]


if __name__ == "__main__":
    import uvicorn

    host = os.getenv('FASTAPI_HOST', '127.0.0.1')
    port = int(os.getenv('FASTAPI_PORT', '8001'))
    print(f"Menjalankan FastAPI di http://{host}:{port}  (docs: /docs)")
    uvicorn.run(app, host=host, port=port)
