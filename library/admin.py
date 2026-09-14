from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Genre, Book, Shelf, UserProfile, ActivityLog


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'books_count', 'is_active', 'color_code', 'icon']
    list_filter = ['is_active']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}

    def books_count(self, obj):
        return obj.books.count()
    books_count.short_description = 'Jumlah Buku'


@admin.register(Shelf)
class ShelfAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'capacity', 'books_count', 'fill_percent', 'is_active', 'color_code']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'description']

    def books_count(self, obj):
        return obj.books.count()
    books_count.short_description = 'Jumlah Buku'

    def fill_percent(self, obj):
        pct = obj.fill_percent
        return f'{pct}%' if pct is not None else '—'
    fill_percent.short_description = 'Keterisian'


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'isbn', 'genre', 'book_type', 'shelf',
                    'publication_year', 'purchase_year', 'recorded_by', 'status', 'rating', 'created_at']
    list_filter = ['status', 'book_type', 'genre', 'shelf', 'recorded_by', 'created_at']
    search_fields = ['title', 'author', 'isbn', 'publisher', 'title_normalized', 'author_normalized']
    readonly_fields = ['created_at', 'updated_at', 'display_cover', 'title_normalized', 'author_normalized']
    list_select_related = ['genre', 'shelf', 'recorded_by']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Informasi Utama', {
            'fields': ('title', 'author', 'isbn', 'genre', 'book_type', 'shelf', 'recorded_by')
        }),
        ('Detail Buku', {
            'fields': ('publication_year', 'purchase_year', 'publisher', 'pages', 'status', 'rating')
        }),
        ('Sampul & Sinopsis', {
            'fields': ('cover_image', 'cover_url', 'display_cover', 'summary')
        }),
        ('Kunci Normalisasi (otomatis)', {
            'fields': ('title_normalized', 'author_normalized'),
            'classes': ('collapse',),
            'description': 'Dipakai untuk deteksi duplikat tanpa peka huruf besar/kecil & spasi ganda.',
        }),
        ('Timestamp', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'avatar_preview', 'theme_preference', 'updated_at']
    list_filter = ['theme_preference']
    search_fields = ['user__username', 'user__email', 'bio']
    readonly_fields = ['avatar_preview', 'updated_at']

    def avatar_preview(self, obj):
        if obj.avatar:
            from django.utils.html import format_html
            return format_html('<img src="{}" width="40" height="40" style="border-radius: 50%;" />', obj.avatar.url)
        return '-'
    avatar_preview.short_description = 'Avatar'


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'detail', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'detail']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profil'
    fields = ['avatar', 'bio', 'phone', 'theme_preference']


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'groups']


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.site_header = "Hirunaza's Library — Admin"
admin.site.site_title = "Hirunaza's Library"
admin.site.index_title = 'Panel Administrasi'
