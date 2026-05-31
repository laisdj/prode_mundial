from apscheduler.schedulers.background import BackgroundScheduler


def actualizar():
    from django.core.management import call_command
    call_command('actualizar_resultados')


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        actualizar,
        'interval',
        minutes=10,
        id='actualizar_resultados',
        replace_existing=True,
    )
    scheduler.start()