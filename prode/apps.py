from django.apps import AppConfig


class ProdeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'prode'

    def ready(self):
        pass
        # from .scheduler import start
        # start()