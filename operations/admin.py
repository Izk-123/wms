from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    Project, MaterialRequest, MaterialRequestItem,
    MaterialReturn, MaterialReturnItem
)


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    list_display = ('code', 'name', 'project_type', 'status', 'supervisor')
    list_filter = ('status', 'project_type')
    search_fields = ('code', 'name')


@admin.register(MaterialRequest)
class MaterialRequestAdmin(ModelAdmin):
    list_display = (
        'reference', 'project', 'requested_by',
        'warehouse', 'status', 'created_at'
    )
    list_filter = ('status',)