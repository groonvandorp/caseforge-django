"""
System monitoring utilities for tracking Celery workers, tasks, and system health
"""
import sqlite3
import subprocess
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.conf import settings
from celery import Celery
from celery.events.state import State
from celery.app.control import Control
import logging

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitor system health, Celery workers, and task queues"""
    
    def __init__(self):
        self.celery_app = Celery('caseforge')
        self.celery_app.config_from_object('caseforge.settings', namespace='CELERY')
        
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'workers': self.get_worker_status(),
            'queues': self.get_queue_status(),
            'tasks': self.get_task_status(),
            'system': self.get_system_health(),
            'dependencies': self.get_dependency_status()
        }
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get Celery worker status"""
        try:
            # Get running celery processes first
            running_processes = self._get_celery_processes()
            
            # Try to get worker stats using celery inspect
            inspect = self.celery_app.control.inspect()
            stats = inspect.stats() or {}
            active = inspect.active() or {}
            registered = inspect.registered() or {}
            
            workers = []
            
            # If inspect works, use detailed worker info
            if stats:
                for worker_name, worker_stats in stats.items():
                    worker_info = {
                        'name': worker_name,
                        'status': 'active' if worker_name in active else 'inactive',
                        'pool': worker_stats.get('pool', {}).get('implementation', 'unknown'),
                        'processes': worker_stats.get('pool', {}).get('processes', 0),
                        'max_concurrency': worker_stats.get('pool', {}).get('max-concurrency', 0),
                        'rusage': worker_stats.get('rusage', {}),
                        'load_avg': worker_stats.get('load', [0, 0, 0]),
                        'tasks_active': len(active.get(worker_name, [])),
                        'registered_tasks': len(registered.get(worker_name, [])),
                        'last_heartbeat': datetime.now().isoformat()
                    }
                    workers.append(worker_info)
            else:
                # Fallback: If inspect doesn't work but we have processes, create worker info from processes
                for i, process in enumerate(running_processes):
                    if process['type'] == 'worker':
                        worker_info = {
                            'name': f"worker-{process['pid']}",
                            'status': 'active',
                            'pool': 'prefork',
                            'processes': 1,
                            'max_concurrency': 4,  # Default assumption
                            'rusage': {},
                            'load_avg': [0, 0, 0],
                            'tasks_active': 0,  # Can't determine without inspect
                            'registered_tasks': 0,  # Can't determine without inspect
                            'last_heartbeat': datetime.now().isoformat(),
                            'note': 'Process detected, inspect unavailable'
                        }
                        workers.append(worker_info)
            
            # Count workers from processes if inspect failed
            worker_count = len([p for p in running_processes if p['type'] == 'worker'])
            
            return {
                'total_workers': len(workers) if workers else worker_count,
                'active_workers': len([w for w in workers if w['status'] == 'active']) if workers else worker_count,
                'workers': workers,
                'processes': running_processes,
                'inspect_available': bool(stats),
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting worker status: {e}")
            return {
                'error': str(e),
                'total_workers': 0,
                'active_workers': 0,
                'workers': [],
                'processes': self._get_celery_processes(),
                'last_check': datetime.now().isoformat()
            }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get task queue status from broker database"""
        try:
            broker_db_path = os.path.join(settings.BASE_DIR, 'celery.db')
            results_db_path = os.path.join(settings.BASE_DIR, 'celery_results.db')
            
            queue_info = {}
            
            # Check broker queue
            if os.path.exists(broker_db_path):
                conn = sqlite3.connect(broker_db_path)
                cursor = conn.cursor()
                
                # Get queue statistics
                cursor.execute('SELECT COUNT(*) FROM kombu_message')
                total_messages = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM kombu_message WHERE visible = 1')
                visible_messages = cursor.fetchone()[0]
                
                queue_info['broker'] = {
                    'total_messages': total_messages,
                    'visible_messages': visible_messages,
                    'database_size': os.path.getsize(broker_db_path)
                }
                conn.close()
            
            # Check results database
            if os.path.exists(results_db_path):
                conn = sqlite3.connect(results_db_path)
                cursor = conn.cursor()
                
                # Get task statistics
                cursor.execute('SELECT status, COUNT(*) FROM celery_taskmeta GROUP BY status')
                status_counts = dict(cursor.fetchall())
                
                cursor.execute('SELECT COUNT(*) FROM celery_taskmeta WHERE date_done > datetime("now", "-1 hour")')
                recent_tasks = cursor.fetchone()[0]
                
                # Count active tasks (PENDING, STARTED, PROGRESS, RETRY)
                cursor.execute('''SELECT COUNT(*) FROM celery_taskmeta 
                               WHERE status IN ("PENDING", "STARTED", "PROGRESS", "RETRY")''')
                active_tasks = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM celery_taskmeta WHERE status = "SUCCESS" AND date_done > datetime("now", "-24 hours")')
                successful_today = cursor.fetchone()[0]
                
                queue_info['results'] = {
                    'status_counts': status_counts,
                    'recent_tasks_1h': recent_tasks,
                    'active_tasks': active_tasks,
                    'successful_today': successful_today,
                    'database_size': os.path.getsize(results_db_path)
                }
                conn.close()
            
            return queue_info
            
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {'error': str(e)}
    
    def get_task_status(self) -> Dict[str, Any]:
        """Get recent task execution status"""
        try:
            results_db_path = os.path.join(settings.BASE_DIR, 'celery_results.db')
            
            if not os.path.exists(results_db_path):
                return {'error': 'Results database not found'}
            
            conn = sqlite3.connect(results_db_path)
            cursor = conn.cursor()
            
            # Get recent tasks
            cursor.execute('''
                SELECT task_id, name, status, date_done, result, traceback 
                FROM celery_taskmeta 
                ORDER BY id DESC 
                LIMIT 10
            ''')
            recent_tasks = []
            for row in cursor.fetchall():
                task_info = {
                    'task_id': row[0],
                    'name': row[1],
                    'status': row[2],
                    'date_done': row[3],
                    'has_result': bool(row[4]),
                    'has_error': bool(row[5])
                }
                recent_tasks.append(task_info)
            
            # Get task performance metrics
            cursor.execute('''
                SELECT 
                    AVG(CASE WHEN status = 'SUCCESS' THEN 
                        (julianday(date_done) - julianday(date_done)) * 24 * 3600 
                    END) as avg_duration_seconds,
                    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as success_count,
                    COUNT(CASE WHEN status = 'FAILURE' THEN 1 END) as failure_count
                FROM celery_taskmeta 
                WHERE date_done > datetime('now', '-24 hours')
            ''')
            metrics = cursor.fetchone()
            
            conn.close()
            
            return {
                'recent_tasks': recent_tasks,
                'metrics': {
                    'avg_duration': metrics[0] or 0,
                    'success_count_24h': metrics[1],
                    'failure_count_24h': metrics[2],
                    'success_rate': (metrics[1] / (metrics[1] + metrics[2]) * 100) if (metrics[1] + metrics[2]) > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return {'error': str(e)}
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system resource health"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available,
                    'percent': psutil.virtual_memory().percent
                },
                'disk': {
                    'total': psutil.disk_usage('/').total,
                    'free': psutil.disk_usage('/').free,
                    'percent': psutil.disk_usage('/').percent
                },
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {'error': str(e)}
    
    def get_dependency_status(self) -> Dict[str, Any]:
        """Check status of key dependencies"""
        dependencies = {}
        
        # Check OpenAI
        try:
            from core.models import AdminSettings
            openai_key = AdminSettings.get_setting('OPENAI_API_KEY')
            dependencies['openai'] = {
                'status': 'configured' if openai_key else 'not_configured',
                'key_present': bool(openai_key),
                'key_preview': f"{openai_key[:8]}...{openai_key[-4:]}" if openai_key else None
            }
        except Exception as e:
            dependencies['openai'] = {'status': 'error', 'error': str(e)}
        
        # Check database connections
        try:
            from django.db import connection
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            dependencies['database'] = {'status': 'connected'}
        except Exception as e:
            dependencies['database'] = {'status': 'error', 'error': str(e)}
        
        # Check Celery broker
        broker_path = os.path.join(settings.BASE_DIR, 'celery.db')
        dependencies['celery_broker'] = {
            'status': 'available' if os.path.exists(broker_path) else 'missing',
            'path': broker_path,
            'size': os.path.getsize(broker_path) if os.path.exists(broker_path) else 0
        }
        
        return dependencies
    
    def _get_celery_processes(self) -> List[Dict[str, Any]]:
        """Get running Celery processes"""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cpu_percent', 'memory_percent']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'celery' in cmdline and 'caseforge' in cmdline:
                        # Determine process type
                        if 'worker' in cmdline:
                            process_type = 'worker'
                        elif 'beat' in cmdline:
                            process_type = 'beat'
                        else:
                            process_type = 'other'
                        
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'type': process_type,
                            'cmdline': cmdline,
                            'started': datetime.fromtimestamp(proc.info['create_time']).isoformat(),
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_percent': proc.info['memory_percent']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error getting Celery processes: {e}")
        
        return processes
    
    def get_worker_health_summary(self) -> str:
        """Get a simple health summary for admin display"""
        try:
            status = self.get_system_status()
            
            worker_count = status['workers']['active_workers']
            queue_active = status['queues'].get('results', {}).get('active_tasks', 0)
            recent_success = status['tasks']['metrics']['success_count_24h']
            
            if worker_count == 0:
                return "🔴 No active workers"
            elif queue_active > 0:
                return f"🟡 {worker_count} workers active, {queue_active} tasks processing"
            elif recent_success > 0:
                return f"🟢 {worker_count} workers active, {recent_success} tasks completed today"
            else:
                return f"🟡 {worker_count} workers active, no recent activity"
                
        except Exception as e:
            return f"❌ Monitor error: {str(e)}"

# Global monitor instance
system_monitor = SystemMonitor()