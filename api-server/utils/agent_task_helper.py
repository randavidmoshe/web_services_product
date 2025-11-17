# Helper for Celery Crawl Tasks to Create Agent Tasks
# Location: api-server/utils/agent_task_helper.py
# USE THIS IN YOUR CELERY CRAWL TASKS

import requests
import os

API_URL = os.getenv('API_URL', 'http://localhost:8001')


def create_agent_task(company_id: int, user_id: int, task_type: str, parameters: dict):
    """
    Helper function for Celery crawl tasks to create agent tasks
    
    Example usage in your discover_form_pages_task:
    
        from utils.agent_task_helper import create_agent_task
        
        # Create agent task to navigate
        task_id = create_agent_task(
            company_id=1,
            user_id=1,
            task_type='navigate_url',
            parameters={'url': 'https://example.com', 'browser': 'chrome'}
        )
        
        # Wait for result
        result = wait_for_agent_result(task_id)
    """
    response = requests.post(
        f"{API_URL}/api/agent/create-task",
        json={
            "company_id": company_id,
            "user_id": user_id,
            "task_type": task_type,
            "parameters": parameters
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        return data.get('task_id')
    else:
        raise Exception(f"Failed to create agent task: {response.text}")


def wait_for_agent_result(task_id: str, timeout: int = 300, poll_interval: int = 2):
    """
    Wait for agent task to complete and return result
    
    Args:
        task_id: Task ID to wait for
        timeout: Max seconds to wait (default 5 minutes)
        poll_interval: Seconds between status checks (default 2)
    
    Returns:
        Task result dict
    
    Raises:
        TimeoutError: If task doesn't complete in time
        Exception: If task fails
    """
    import time
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(
            f"{API_URL}/api/agent/task-status/{task_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            
            if status == 'completed':
                return data.get('result')
            elif status == 'failed':
                error = data.get('error_message', 'Unknown error')
                raise Exception(f"Agent task failed: {error}")
        
        time.sleep(poll_interval)
    
    raise TimeoutError(f"Agent task {task_id} did not complete within {timeout} seconds")


def create_and_wait_for_agent_task(company_id: int, user_id: int, task_type: str, parameters: dict, timeout: int = 300):
    """
    Convenience function: create agent task and wait for result in one call
    
    Example:
        result = create_and_wait_for_agent_task(
            company_id=1,
            user_id=1,
            task_type='navigate_url',
            parameters={'url': 'https://example.com'}
        )
        
        dom = result.get('dom')
    """
    task_id = create_agent_task(company_id, user_id, task_type, parameters)
    return wait_for_agent_result(task_id, timeout)
