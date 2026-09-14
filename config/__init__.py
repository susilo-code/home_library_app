"""
Shim driver MySQL opsional.

Bila Anda memakai MySQL/MariaDB (mis. Laragon) TANPA ingin mengompilasi
mysqlclient, cukup pasang PyMySQL:

    pip install PyMySQL

Blok di bawah akan otomatis membuat Django memakai PyMySQL sebagai
pengganti MySQLdb. Jika PyMySQL tidak terpasang, baris ini dilewati
sehingga SQLite/PostgreSQL tetap berjalan normal.
"""

try:  # pragma: no cover - hanya aktif bila PyMySQL tersedia
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass
