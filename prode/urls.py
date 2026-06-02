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
    path('eliminatoria/', views.pronosticos_eliminatoria, name='pronosticos_eliminatoria'),
    path('resultados-eliminatoria/', views.cargar_resultados_eliminatoria, name='cargar_resultados_eliminatoria'),
    path('eliminatoria-resultados/', views.eliminatoria, name='eliminatoria'),
    path('bracket/', views.bracket, name='bracket'),
    path('gestionar-eliminatoria/', views.gestionar_eliminatoria, name='gestionar_eliminatoria'),
    path('chat/', views.chat, name='chat'),
    path('chat/mensajes/', views.chat_mensajes, name='chat_mensajes'),
    path('desafios/', views.desafios, name='desafios'),
    path('desafios/crear/', views.crear_desafio, name='crear_desafio'),
    path('desafios/<int:desafio_id>/responder/', views.responder_desafio, name='responder_desafio'),
    path('usuario/<int:usuario_id>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),path('desafios/historial/', views.historial_desafios, name='historial_desafios'),
    path('chat/borrar/<int:mensaje_id>/', views.borrar_mensaje, name='borrar_mensaje'),
    
]