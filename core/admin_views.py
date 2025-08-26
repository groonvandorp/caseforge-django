"""
Custom admin views for system monitoring
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import JsonResponse
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from .monitoring import system_monitor
import json

@method_decorator(staff_member_required, name='dispatch')
class SystemStatusView(TemplateView):
    """System status dashboard for admin"""
    template_name = 'admin/system_status.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            status = system_monitor.get_system_status()
            context.update({
                'system_status': status,
                'status_json': json.dumps(status, indent=2),
                'title': 'System Status Dashboard',
                'subtitle': 'Monitor Celery workers, tasks, and system health'
            })
        except Exception as e:
            context.update({
                'error': str(e),
                'title': 'System Status Dashboard',
                'subtitle': 'Error retrieving system status'
            })
        
        return context

@staff_member_required
def system_status_api(request):
    """API endpoint for real-time status updates"""
    try:
        status = system_monitor.get_system_status()
        return JsonResponse(status)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required 
def worker_health_api(request):
    """Quick worker health check for admin dashboard"""
    try:
        health = system_monitor.get_worker_health_summary()
        return JsonResponse({'health': health})
    except Exception as e:
        return JsonResponse({'health': f"❌ Error: {str(e)}"}, status=500)

# URL patterns for custom admin views
admin_urlpatterns = [
    path('system-status/', SystemStatusView.as_view(), name='admin_system_status'),
    path('api/system-status/', system_status_api, name='admin_system_status_api'),
    path('api/worker-health/', worker_health_api, name='admin_worker_health_api'),
]