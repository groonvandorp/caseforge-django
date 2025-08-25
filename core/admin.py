from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import (
    ProcessModel, ProcessModelVersion, ProcessNode, SourceDocument,
    NodeDocument, NodeUsecaseCandidate, NodeBookmark, Portfolio,
    PortfolioItem, UserSettings, ModelAccess, NodeEmbedding
)

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_staff', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name']


@admin.register(ProcessModel)
class ProcessModelAdmin(admin.ModelAdmin):
    list_display = ['model_key', 'name', 'created_at']
    search_fields = ['model_key', 'name']
    readonly_fields = ['created_at']


class ProcessModelVersionInline(admin.TabularInline):
    model = ProcessModelVersion
    extra = 0
    readonly_fields = ['created_at']


@admin.register(ProcessModelVersion)
class ProcessModelVersionAdmin(admin.ModelAdmin):
    list_display = ['model', 'version_label', 'is_current', 'effective_date', 'created_at']
    list_filter = ['is_current', 'effective_date', 'created_at']
    search_fields = ['model__name', 'version_label']
    readonly_fields = ['created_at']


@admin.register(ProcessNode)
class ProcessNodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'level', 'model_version', 'parent']
    list_filter = ['level', 'model_version__model__name']
    search_fields = ['code', 'name', 'description']
    raw_id_fields = ['parent']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('model_version__model', 'parent')


@admin.register(NodeDocument)
class NodeDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'node', 'user', 'created_at']
    list_filter = ['document_type', 'created_at']
    search_fields = ['title', 'node__code', 'node__name', 'user__username']
    raw_id_fields = ['node', 'user']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(NodeUsecaseCandidate)
class NodeUsecaseCandidateAdmin(admin.ModelAdmin):
    list_display = ['title', 'node', 'user', 'complexity_score', 'created_at']
    list_filter = ['complexity_score', 'created_at']
    search_fields = ['title', 'candidate_uid', 'node__code', 'user__username']
    raw_id_fields = ['node', 'user']
    readonly_fields = ['created_at']


@admin.register(NodeBookmark)
class NodeBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'node', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'node__code', 'node__name']
    raw_id_fields = ['node', 'user']


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at']
    search_fields = ['name', 'user__username']
    raw_id_fields = ['user']


@admin.register(ModelAccess)
class ModelAccessAdmin(admin.ModelAdmin):
    list_display = ['user', 'model', 'granted_at']
    list_filter = ['granted_at']
    search_fields = ['user__username', 'model__name']
    raw_id_fields = ['user', 'model']


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'theme', 'preferred_model']
    list_filter = ['theme']
    search_fields = ['user__username']
    raw_id_fields = ['user', 'preferred_model']
    
    fieldsets = [
        ('User', {
            'fields': ['user']
        }),
        ('Appearance', {
            'fields': ['theme'],
            'description': 'Choose your preferred theme for the admin interface'
        }),
        ('Preferences', {
            'fields': ['preferred_model', 'settings_json'],
            'classes': ['collapse']
        }),
    ]
    
    def get_or_create_for_user(self, user):
        obj, created = UserSettings.objects.get_or_create(
            user=user,
            defaults={'theme': 'dark'}
        )
        return obj
