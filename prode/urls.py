from django.urls import path
from . import views

urlpatterns = [
    path('',              views.ranking,      name='ranking'),
    path('partidos/',     views.partidos,     name='partidos'),
    path('pronosticos/',  views.pronosticos,  name='pronosticos'),
    path('login/',        views.login_view,   name='login'),
    path('logout/',       views.logout_view,  name='logout'),
    path('registro/',     views.registro,     name='registro'),
    path('resultados/', views.cargar_resultados, name='cargar_resultados'),
    path('reglas/', views.reglas, name='reglas'),
    path('clasificacion/', views.clasificacion, name='clasificacion'),
    path('mi-clasificacion/', views.mi_clasificacion, name='mi_clasificacion'),
    path('equipos-eliminatoria/', views.cargar_equipos_eliminatoria, name='cargar_equipos_eliminatoria'),
]