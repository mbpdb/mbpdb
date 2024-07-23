# tasks.py

from celery import shared_task
from django.core.cache import cache
import time

@shared_task(bind=True)
def long_running_task(self):
    start_time = time.time()
    for i in range(500):  # Simulating a task that runs in 100 steps
        time.sleep(1)  # Simulate a delay for each step
        elapsed_time = time.time() - start_time
        # Update progress in cache
        cache.set(f'progress_{self.request.id}', i, timeout=3600)
        cache.set(f'elapsed_time_{self.request.id}', elapsed_time, timeout=3600)  # Elapsed time in seconds
        print(f'Cache set: progress_{self.request.id} = {i}, elapsed_time_{self.request.id} = {elapsed_time}')
    return 'Task complete'