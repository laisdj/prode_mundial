from django.conf import settings

def fase2(request):
    return {'fase2_activa': settings.FASE2_ACTIVA}