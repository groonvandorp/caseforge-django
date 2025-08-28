import logging
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.urls import path
from django.shortcuts import render
from django.http import JsonResponse
from django.template.response import TemplateResponse
from .models import (
    ProcessModel, ProcessModelVersion, ProcessNode, SourceDocument,
    NodeDocument, NodeUsecaseCandidate, NodeBookmark, Portfolio,
    PortfolioItem, UserSettings, ModelAccess, NodeEmbedding, AdminSettings
)
# from .monitoring import system_monitor

User = get_user_model()
logger = logging.getLogger(__name__)


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
    list_display = ['code', 'name', 'level', 'model_version', 'parent', 'has_process_details']
    list_filter = ['level', 'model_version__model__name']
    search_fields = ['code', 'name', 'description']
    raw_id_fields = ['parent']
    actions = ['delete_node_process_details']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('model_version__model', 'parent')
    
    @admin.display(boolean=True, description='Has Process Details')
    def has_process_details(self, obj):
        return NodeDocument.objects.filter(node=obj, document_type='process_details').exists()
    
    @admin.action(description='Delete process details for selected nodes')
    def delete_node_process_details(self, request, queryset):
        deleted_count = 0
        deleted_nodes = []
        
        logger.info(f"Admin bulk delete process details started by user {request.user.username} for {queryset.count()} nodes")
        
        for node in queryset:
            process_details = NodeDocument.objects.filter(node=node, document_type='process_details')
            if process_details.exists():
                # Log each deletion
                for doc in process_details:
                    logger.info(
                        f"Admin process details deletion - User: {request.user.username} (ID: {request.user.id}), "
                        f"Node: {node.code} - {node.name} (ID: {node.id}), "
                        f"Document ID: {doc.id}, Document created: {doc.created_at}"
                    )
                
                process_details.delete()
                deleted_count += 1
                deleted_nodes.append(f"{node.code} ({node.name})")
        
        if deleted_count == 0:
            logger.info(f"Admin bulk delete - No process details found by user {request.user.username}")
            self.message_user(request, "No process details documents found for the selected nodes.", messages.WARNING)
            return
        
        if deleted_count == 1:
            message = f"Successfully deleted process details document for node {deleted_nodes[0]}"
        else:
            message = f"Successfully deleted process details documents for {deleted_count} nodes: {', '.join(deleted_nodes[:3])}"
            if len(deleted_nodes) > 3:
                message += f" and {len(deleted_nodes) - 3} more"
        
        logger.info(f"Admin bulk delete completed - {deleted_count} process details deleted by user {request.user.username}")
        self.message_user(request, message, messages.SUCCESS)


@admin.register(NodeDocument)
class NodeDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'node', 'created_at']
    list_filter = ['document_type', 'created_at']
    search_fields = ['title', 'node__code', 'node__name']
    raw_id_fields = ['node']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['delete_process_details']
    
    @admin.action(description='Delete selected process details documents')
    def delete_process_details(self, request, queryset):
        process_details = queryset.filter(document_type='process_details')
        deleted_count = process_details.count()
        
        if deleted_count == 0:
            self.message_user(request, "No process details documents were selected.", messages.WARNING)
            return
        
        # Store info about what we're deleting for the message
        deleted_info = list(process_details.values_list('node__code', 'node__name'))
        
        # Delete the documents
        process_details.delete()
        
        # Create a detailed message
        if deleted_count == 1:
            node_code, node_name = deleted_info[0]
            message = f"Successfully deleted process details document for node {node_code} ({node_name})"
        else:
            message = f"Successfully deleted {deleted_count} process details documents"
        
        self.message_user(request, message, messages.SUCCESS)


@admin.register(NodeUsecaseCandidate)
class NodeUsecaseCandidateAdmin(admin.ModelAdmin):
    list_display = ['title', 'node', 'complexity_score', 'created_at']
    list_filter = ['complexity_score', 'created_at']
    search_fields = ['title', 'candidate_uid', 'node__code']
    raw_id_fields = ['node']
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


@admin.register(AdminSettings)
class AdminSettingsAdmin(admin.ModelAdmin):
    list_display = ['key', 'value_preview', 'description', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['key', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Setting Information', {
            'fields': ['key', 'description']
        }),
        ('Value', {
            'fields': ['value'],
            'description': 'Enter the setting value. For API keys, this will be securely stored.'
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def value_preview(self, obj):
        """Show a preview of the value, hiding sensitive data"""
        if not obj.value:
            return "None"
        
        # Hide API keys and sensitive data
        if 'api_key' in obj.key.lower() or 'secret' in obj.key.lower() or 'token' in obj.key.lower():
            if len(obj.value) > 10:
                return f"{obj.value[:6]}...{obj.value[-4:]}"
            else:
                return "***hidden***"
        
        # Truncate long values
        if len(obj.value) > 50:
            return f"{obj.value[:47]}..."
        
        return obj.value
    
    value_preview.short_description = 'Value'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Add help text for common settings
        if obj and obj.key == 'openai_api_key':
            form.base_fields['value'].help_text = 'Your OpenAI API key (starts with sk-...)'
        elif obj and obj.key == 'openai_model':
            form.base_fields['value'].help_text = 'OpenAI model to use (e.g., gpt-4o, gpt-3.5-turbo)'
        
        return form


# Custom Admin Site with System Monitoring
class SystemMonitoringAdminSite(admin.AdminSite):
    """Custom admin site with system monitoring capabilities"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('system-status/', self.admin_view(self.system_status_view), name='system_status'),
            path('api/worker-health/', self.admin_view(self.worker_health_api), name='worker_health_api'),
        ]
        return custom_urls + urls
    
    def system_status_view(self, request):
        """System status dashboard view"""
        try:
            status = {} # system_monitor.get_system_status()
            context = {
                **self.each_context(request),
                'system_status': status,
                'title': 'System Status Dashboard',
                'subtitle': 'Monitor Celery workers, tasks, and system health'
            }
            return TemplateResponse(request, 'admin/system_status.html', context)
        except Exception as e:
            context = {
                **self.each_context(request),
                'error': str(e),
                'title': 'System Status Dashboard',
                'subtitle': 'Error retrieving system status'
            }
            return TemplateResponse(request, 'admin/system_status.html', context)
    
    def worker_health_api(self, request):
        """API endpoint for quick worker health status"""
        try:
            health = {} # system_monitor.get_worker_health_summary()
            return JsonResponse({'health': health})
        except Exception as e:
            return JsonResponse({'health': f"❌ Error: {str(e)}"}, status=500)

    def index(self, request, extra_context=None):
        """Override admin index to show system status"""
        context = extra_context or {}
        
        # Add worker health to admin index
        try:
            context['worker_health'] = {} # system_monitor.get_worker_health_summary()
        except Exception as e:
            context['worker_health'] = f"❌ Monitor Error: {str(e)}"
        
        return super().index(request, context)


# Use custom admin site
admin_site = SystemMonitoringAdminSite(name='admin')

# Re-register all models with the custom admin site
admin_site.register(User, UserAdmin)
admin_site.register(ProcessModel, ProcessModelAdmin)
admin_site.register(ProcessModelVersion, ProcessModelVersionAdmin)
admin_site.register(ProcessNode, ProcessNodeAdmin)
admin_site.register(NodeDocument, NodeDocumentAdmin)
admin_site.register(NodeUsecaseCandidate, NodeUsecaseCandidateAdmin)
admin_site.register(NodeBookmark, NodeBookmarkAdmin)
admin_site.register(Portfolio, PortfolioAdmin)
admin_site.register(ModelAccess, ModelAccessAdmin)
admin_site.register(UserSettings, UserSettingsAdmin)
admin_site.register(AdminSettings, AdminSettingsAdmin)
