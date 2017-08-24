from django.contrib import admin

from .models import User as UserProfile, UserMovements


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff','is_superuser')
    list_editable = ('email', 'is_active',)
    ordering = ('username', )


@admin.register(UserMovements)
class UserMovements(admin.ModelAdmin):
    list_display = ('user', 'category', 'creation_date',)
    ordering = ('creation_date',)
