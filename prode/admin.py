from django.contrib import admin
from .models import Partido, Pronostico, PartidoEliminatorio, PronosticoEliminatorio


@admin.register(Partido)
class PartidoAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'grupo', 'fecha', 'goles_l', 'goles_v', 'jugado']
    list_filter   = ['grupo', 'jugado']
    list_editable = ['goles_l', 'goles_v', 'jugado']
    ordering      = ['fecha']


@admin.register(Pronostico)
class PronosticoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'partido', 'goles_l', 'goles_v']
    list_filter  = ['usuario']


@admin.register(PartidoEliminatorio)
class PartidoEliminatórioAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'ronda', 'orden', 'local', 'visita', 'goles_l', 'goles_v', 'jugado']
    list_filter   = ['ronda', 'jugado']
    list_editable = ['local', 'visita', 'goles_l', 'goles_v', 'jugado']
    ordering      = ['orden']


@admin.register(PronosticoEliminatorio)
class PronosticoEliminatórioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'partido', 'goles_l', 'goles_v']
    list_filter  = ['usuario']