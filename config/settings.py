"""
Django settings — Hirunaza's Library Information System

Konfigurasi dibaca dari file .env (python-dotenv) agar mudah dipindah antar PC.
Salin .env.example menjadi .env, atau jalankan setup.bat untuk otomatis.
"""
from pathlib import Path
import os

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Muat variabel lingkungan dari .env ────────────────────────────────────────
load_dotenv(BASE_DIR / '.env')


def env_bool(name: str, default: bool = False) -> bool:
    """True/False dari .env dengan toleransi penulisan (true/1/yes/on)."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'y', 'on')


def env_list(name: str, default: str = '') -> list[str]:
    """Daftar dipisah koma dari .env -> list of str."""
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


def env_int(name: str, default: int) -> int:
    """Bilangan bulat dari .env; nilai tidak valid/absen -> default."""
    try:
        return int(str(os.getenv(name, default)).strip())
    except (TypeError, ValueError):
        return int(default)


# ── Keamanan dasar ────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-ganti-key-ini-di-file-env')
DEBUG = env_bool('DEBUG', True)
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', '127.0.0.1,localhost,testserver') or ['127.0.0.1', 'localhost']

# Diperlukan untuk login/logout saat diakses lewat proxy/hostname lain (opsional)
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', '')


# ── Aplikasi ──────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "library",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Pengembangan: jangan biarkan browser meng-cache apa pun, supaya perubahan
# template/CSS langsung terlihat tanpa hard-refresh (lihat config/middleware.py).
if DEBUG:
    MIDDLEWARE.append("config.middleware.TanpaCacheDevMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Identitas aplikasi (judul dinamis) untuk semua template
                "library.context_processors.identitas_aplikasi",
                # Versi aset statik -> ?v= pada CSS/JS (anti cache lama)
                "library.context_processors.static_version",
                # Info sesi (batas idle + penanda sesi berakhir)
                "library.context_processors.sesi_info",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ── Database: sqlite | mysql | postgres (dipilih dari .env) ───────────────────
DB_ENGINE = os.getenv('DB_ENGINE', 'sqlite').strip().lower()
DB_NAME = os.getenv('DB_NAME', 'db.sqlite3').strip()
DB_USER = os.getenv('DB_USER', '').strip()
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', '127.0.0.1').strip()
DB_PORT = os.getenv('DB_PORT', '3307').strip()

if DB_ENGINE in ('mysql', 'mariadb'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
elif DB_ENGINE in ('postgres', 'postgresql', 'pgsql'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT or '5432',
        }
    }
else:
    # Default: SQLite — tidak perlu server DB, paling aman untuk PC baru
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / DB_NAME,
        }
    }


# ── Validasi kata sandi ───────────────────────────────────────────────────────
# Dikosongkan sesuai permintaan: kata sandi DIBEBASKAN — tanpa aturan panjang
# minimum, tanpa penolakan kata sandi umum/angka saja.
AUTH_PASSWORD_VALIDATORS = []


# ── Bahasa & waktu ────────────────────────────────────────────────────────────
LANGUAGE_CODE = "id"
TIME_ZONE = os.getenv('TIME_ZONE', 'Asia/Jakarta')
USE_I18N = True
USE_TZ = True


# ── Static & media ────────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


# ── Lain-lain ─────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"


# ── Sesi: keluar otomatis setelah TIDAK ADA AKTIVITAS (default 10 menit) ──────
# SESSION_IDLE_MINUTES dapat diubah dari .env tanpa menyentuh kode.
#   • SESSION_COOKIE_AGE     = batas usia cookie sesi.
#   • SESSION_SAVE_EVERY_REQUEST = setiap permintaan memperbarui masa berlaku
#     -> hitungannya "10 menit sejak aktivitas terakhir" (jendela bergeser),
#     BUKAN "10 menit sejak login". Tanpa ini semua orang ter-logout 10 menit
#     setelah masuk walaupun sedang aktif memakai aplikasi.
#   • SESSION_EXPIRE_AT_BROWSER_CLOSE = menutup browser mengakhiri sesi, sehingga
#     membuka aplikasi lagi selalu mulai dari halaman LOGIN.
SESSION_IDLE_MINUTES = max(1, env_int('SESSION_IDLE_MINUTES', 10))
SESSION_COOKIE_AGE = SESSION_IDLE_MINUTES * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
