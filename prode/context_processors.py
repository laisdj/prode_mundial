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




def mensajes_nuevos(request):
    if request.user.is_authenticated:
        from .models import PerfilUsuario, Mensaje
        from django.utils import timezone
        try:
            perfil = PerfilUsuario.objects.get(usuario=request.user)
            if perfil.ultima_visita_chat:
                count = Mensaje.objects.filter(
                    creado_en__gt=perfil.ultima_visita_chat
                ).exclude(usuario=request.user).count()
            else:
                count = Mensaje.objects.exclude(usuario=request.user).count()
        except PerfilUsuario.DoesNotExist:
            count = Mensaje.objects.exclude(usuario=request.user).count()
        return {'mensajes_nuevos': count}
    return {'mensajes_nuevos': 0}