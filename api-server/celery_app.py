from celery import Celery
import os
from datetime import datetime
from typing import Dict, Any

import logging

# Configure logging for Celery workers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Redis URL
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Create Celery app
celery = Celery(
    "form_discoverer",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['tasks.form_mapper_tasks', 'tasks.forms_runner_tasks', 'tasks.form_pages_tasks', 'tasks.user_requirements_tasks', 'tasks.pom_generator_tasks']
)

# Celery configuration
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
)

celery.conf.beat_schedule = {
    'cleanup-stale-sessions-hourly': {
        'task': 'tasks.cleanup_stale_mapper_sessions',
        'schedule': 3600.0,
    },
    'cleanup-stale-crawl-sessions-hourly': {
        'task': 'tasks.cleanup_stale_crawl_sessions',
        'schedule': 3600.0,
    },
}

@celery.task
def test_task():
    """Simple test task"""
    return "Celery is working!"


# ========== AGENT TASK QUEUE (NEW) ==========

@celery.task(name='agent.execute_test', bind=True)
def execute_test_task(self, company_id: int, user_id: int, test_url: str, test_steps: list, **kwargs):
    """
    Task for agent to execute a test
    Agent polls this queue and executes
    """
    task_id = self.request.id
    
    # Update state to PENDING (waiting for agent)
    self.update_state(
        state='PENDING',
        meta={
            'status': 'Waiting for agent to pick up task',
            'task_type': 'execute_test',
            'created_at': datetime.utcnow().isoformat()
        }
    )
    
    # Task stays in queue until agent picks it up
    return {
        'task_id': task_id,
        'task_type': 'execute_test',
        'company_id': company_id,
        'user_id': user_id,
        'test_url': test_url,
        'test_steps': test_steps,
        **kwargs
    }


@celery.task(name='agent.navigate_url', bind=True)
def navigate_url_task(self, company_id: int, user_id: int, url: str, **kwargs):
    """Task for agent to navigate to URL"""
    task_id = self.request.id
    
    self.update_state(
        state='PENDING',
        meta={
            'status': 'Waiting for agent',
            'task_type': 'navigate_url',
            'created_at': datetime.utcnow().isoformat()
        }
    )
    
    return {
        'task_id': task_id,
        'task_type': 'navigate_url',
        'company_id': company_id,
        'user_id': user_id,
        'url': url,
        **kwargs
    }


@celery.task(name='agent.extract_dom', bind=True)
def extract_dom_task(self, company_id: int, user_id: int, **kwargs):
    """Task for agent to extract DOM"""
    task_id = self.request.id
    
    self.update_state(
        state='PENDING',
        meta={
            'status': 'Waiting for agent',
            'task_type': 'extract_dom',
            'created_at': datetime.utcnow().isoformat()
        }
    )
    
    return {
        'task_id': task_id,
        'task_type': 'extract_dom',
        'company_id': company_id,
        'user_id': user_id,
        **kwargs
    }


@celery.task(name='agent.execute_steps', bind=True)
def execute_steps_task(self, company_id: int, user_id: int, steps: list, **kwargs):
    """Task for agent to execute steps"""
    task_id = self.request.id
    
    self.update_state(
        state='PENDING',
        meta={
            'status': 'Waiting for agent',
            'task_type': 'execute_steps',
            'created_at': datetime.utcnow().isoformat()
        }
    )
    
    return {
        'task_id': task_id,
        'task_type': 'execute_steps',
        'company_id': company_id,
        'user_id': user_id,
        'steps': steps,
        **kwargs
    }


# ========== RESULT CALLBACKS (NEW) ==========

@celery.task(name='agent.task_completed')
def agent_task_completed(task_id: str, result: Dict[str, Any]):
    """Called by agent when task completes successfully"""
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id, app=celery)
    task.update_state(
        state='SUCCESS',
        meta={
            'status': 'completed',
            'result': result,
            'completed_at': datetime.utcnow().isoformat()
        }
    )
    
    return {'success': True, 'task_id': task_id}


@celery.task(name='agent.task_failed')
def agent_task_failed(task_id: str, error: str):
    """Called by agent when task fails"""
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id, app=celery)
    task.update_state(
        state='FAILURE',
        meta={
            'status': 'failed',
            'error': error,
            'failed_at': datetime.utcnow().isoformat()
        }
    )
    
    return {'success': False, 'task_id': task_id, 'error': error}


@celery.task(name='agent.task_progress')
def agent_task_progress(task_id: str, progress: int, message: str):
    """Called by agent to update task progress"""
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id, app=celery)
    task.update_state(
        state='PROGRESS',
        meta={
            'status': 'running',
            'progress': progress,
            'message': message,
            'updated_at': datetime.utcnow().isoformat()
        }
    )
    
    return {'success': True, 'task_id': task_id}


# ========== HELPER FUNCTIONS (NEW) ==========

def get_pending_agent_tasks(company_id: int = None, limit: int = 10):
    """
    Get list of pending agent tasks from Redis
    Used by agents to poll for work
    """
    from celery.result import AsyncResult
    
    inspector = celery.control.inspect()
    scheduled = inspector.scheduled()
    reserved = inspector.reserved()
    
    pending_tasks = []
    
    # Check scheduled tasks
    if scheduled:
        for worker, tasks in scheduled.items():
            for task in tasks[:limit]:
                if task['name'].startswith('agent.'):
                    result = AsyncResult(task['id'], app=celery)
                    if result.state == 'PENDING':
                        task_data = result.info if result.info else {}
                        if company_id is None or task_data.get('company_id') == company_id:
                            pending_tasks.append({
                                'task_id': task['id'],
                                'task_type': task_data.get('task_type'),
                                'parameters': task_data
                            })
    
    # Check reserved tasks
    if reserved:
        for worker, tasks in reserved.items():
            for task in tasks[:limit]:
                if task['name'].startswith('agent.'):
                    result = AsyncResult(task['id'], app=celery)
                    if result.state == 'PENDING':
                        task_data = result.info if result.info else {}
                        if company_id is None or task_data.get('company_id') == company_id:
                            pending_tasks.append({
                                'task_id': task['id'],
                                'task_type': task_data.get('task_type'),
                                'parameters': task_data
                            })
    
    return pending_tasks[:limit]


def get_task_status(task_id: str):
    """Get status of a Celery task"""
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery)
    
    return {
        'task_id': task_id,
        'state': result.state,
        'info': result.info if result.info else {},
        'successful': result.successful(),
        'failed': result.failed(),
        'ready': result.ready()
    }


# Configure Celery to route agent tasks to a separate queue
# that the celery-worker ignores
celery.conf.task_routes = {
    'agent.execute_test': {'queue': 'agent_only'},
    'agent.navigate_url': {'queue': 'agent_only'},
    'agent.extract_dom': {'queue': 'agent_only'},
    'agent.execute_steps': {'queue': 'agent_only'},
}
