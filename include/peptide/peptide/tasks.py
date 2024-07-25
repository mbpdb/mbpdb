# tasks.py

from celery import shared_task
from django.core.cache import cache
import time
@shared_task(bind=True)
def long_running_task(self):
    start_time = time.time()
    for i in range(360):  # Simulating a task that runs in 60 steps
        time.sleep(1)  # Simulate a delay for each step
        elapsed_time = time.time() - start_time
        # Update progress in cache without timeout
        cache.set(f'progress_{self.request.id}', i)
        cache.set(f'elapsed_time_{self.request.id}', elapsed_time)  # Elapsed time in seconds
        print(f'Cache set: progress_{self.request.id} = {i}, elapsed_time_{self.request.id} = {elapsed_time}')
    # Set task complete status
    cache.set(f'status_{self.request.id}', 'complete')
    return 'Task complete'
