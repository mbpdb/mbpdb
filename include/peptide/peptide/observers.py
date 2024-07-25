# observers.py

class ProgressObserver:
    def __init__(self, task_id):
        self.task_id = task_id
    #def set_progress(self, current, total):
    #    progress = (current / total) * 100
    #    from django.core.cache import cache
    #    cache.set(f'progress_{self.task_id}', progress)
