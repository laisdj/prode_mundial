from django.conf import settings
from .models import Desafio


def fase2(request):
    return {'fase2_activa': settings.FASE2_ACTIVA}


def desafios_pendientes(request):
    if request.user.is_authenticated and not request.user.is_staff:
        count = Desafio.objects.filter(
            retado=request.user,
            estado='pendiente'
        ).count()
        return {'desafios_pendientes': count}
    return {'desafios_pendientes': 0}