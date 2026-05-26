from django.contrib import admin
from .models import Partido, Pronostico


@admin.register(Partido)
class PartidoAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'grupo', 'fecha', 'goles_l', 'goles_v', 'jugado']
    list_filter  = ['grupo', 'jugado']
    list_editable = ['goles_l', 'goles_v', 'jugado']
    ordering     = ['fecha']


@admin.register(Pronostico)
class PronosticoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'partido', 'goles_l', 'goles_v']
    list_filter  = ['usuario']