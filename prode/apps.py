from django.apps import AppConfig


class ProdeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'prode'

    def ready(self):
        import os
        if os.environ.get('RUN_MAIN') or os.environ.get('RAILWAY_ENVIRONMENT'):
            try:
                from .scheduler import start
                start()
            except Exception as e:
                print(f'Scheduler no pudo iniciar: {e}')