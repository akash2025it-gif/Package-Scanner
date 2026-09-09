from app.core.config import settings

try:
    from celery import Celery
    celery_app = Celery(
        "packcheck_tasks",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    )
    celery_app.autodiscover_tasks(["app.workers.tasks"])
except ImportError:
    # Dummy mock class for Celery if running in lightweight local mode without Celery installed
    class DummyCelery:
        def task(self, *args, **kwargs):
            def decorator(func):
                def delay(*f_args, **f_kwargs):
                    return func(*f_args, **f_kwargs)
                func.delay = delay
                return func
            return decorator
    celery_app = DummyCelery()
