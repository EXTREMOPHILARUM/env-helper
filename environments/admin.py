from django.contrib import admin
from .models import Environment

# Register your models here.

@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'environment_type', 'created_by', 'is_running', 'created_at')
    list_filter = ('environment_type', 'is_running', 'created_at')
    search_fields = ('name', 'description', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'container_id', 'is_running')
