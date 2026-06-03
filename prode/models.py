from django.db import models
from django.contrib.auth.models import User


class Partido(models.Model):
    GRUPO_CHOICES = [(g, f"Grupo {g}") for g in "ABCDEFGHIJKL"]

    grupo   = models.CharField(max_length=1, choices=GRUPO_CHOICES)
    fecha   = models.DateTimeField()
    local   = models.CharField(max_length=50)
    visita  = models.CharField(max_length=50)
    goles_l = models.IntegerField(null=True, blank=True)
    goles_v = models.IntegerField(null=True, blank=True)
    jugado  = models.BooleanField(default=False)

    def resultado_real(self):
        if not self.jugado or self.goles_l is None:
            return None
        if self.goles_l > self.goles_v: return 'L'
        if self.goles_l < self.goles_v: return 'V'
        return 'E'

    def __str__(self):
        return f"[{self.grupo}] {self.local} vs {self.visita} — {self.fecha.strftime('%d/%m %H:%M')}"

    class Meta:
        ordering = ['fecha']


class Pronostico(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE)
    goles_l = models.IntegerField(null=True, blank=True)
    goles_v = models.IntegerField(null=True, blank=True)
    nota    = models.CharField(max_length=200, blank=True, default='')

    def resultado_pred(self):
        if self.goles_l is None or self.goles_v is None:
            return None
        if self.goles_l > self.goles_v: return 'L'
        if self.goles_l < self.goles_v: return 'V'
        return 'E'

    def puntos(self):
        real = self.partido.resultado_real()
        pred = self.resultado_pred()
        if real is None or pred is None:
            return 0
        if (self.goles_l == self.partido.goles_l and
                self.goles_v == self.partido.goles_v):
            return 3
        if pred == real:
            return 1
        return 0

    class Meta:
        unique_together = ('usuario', 'partido')

    def __str__(self):
        return f"{self.usuario.username} — {self.partido}"


class PartidoEliminatorio(models.Model):
    RONDA_CHOICES = [
        ('R32', 'Round of 32'),
        ('R16', 'Round of 16'),
        ('QF',  'Cuartos de final'),
        ('SF',  'Semifinal'),
        ('3PL', 'Tercer y cuarto lugar'),
        ('FIN', 'Final'),
    ]

    ronda       = models.CharField(max_length=3, choices=RONDA_CHOICES)
    slot_local  = models.CharField(max_length=50)
    slot_visita = models.CharField(max_length=50)
    local       = models.CharField(max_length=50, blank=True, default='')
    visita      = models.CharField(max_length=50, blank=True, default='')
    goles_l     = models.IntegerField(null=True, blank=True)
    goles_v     = models.IntegerField(null=True, blank=True)
    penales_l   = models.IntegerField(null=True, blank=True)
    penales_v   = models.IntegerField(null=True, blank=True)
    jugado      = models.BooleanField(default=False)
    orden       = models.IntegerField(default=0)

    def resultado_real(self):
        if not self.jugado or self.goles_l is None:
            return None
        if self.goles_l > self.goles_v: return 'L'
        if self.goles_l < self.goles_v: return 'V'
        if self.penales_l is not None and self.penales_v is not None:
            return 'L' if self.penales_l > self.penales_v else 'V'
        return 'E'

    def __str__(self):
        local = self.local or self.slot_local
        visita = self.visita or self.slot_visita
        return f"[{self.ronda}] {local} vs {visita}"

    class Meta:
        ordering = ['orden']


class PronosticoEliminatorio(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    partido = models.ForeignKey(PartidoEliminatorio, on_delete=models.CASCADE)
    local   = models.CharField(max_length=50, blank=True, default='')
    visita  = models.CharField(max_length=50, blank=True, default='')
    goles_l = models.IntegerField(null=True, blank=True)
    goles_v = models.IntegerField(null=True, blank=True)

    def resultado_pred(self):
        if self.goles_l is None or self.goles_v is None:
            return None
        if self.goles_l > self.goles_v: return 'L'
        if self.goles_l < self.goles_v: return 'V'
        return 'E'

    def puntos(self):
        real = self.partido.resultado_real()
        pred = self.resultado_pred()
        if real is None or pred is None:
            return 0
        if (self.goles_l == self.partido.goles_l and
                self.goles_v == self.partido.goles_v):
            return 3
        if pred == real:
            return 1
        return 0

    class Meta:
        unique_together = ('usuario', 'partido')

    def __str__(self):
        return f"{self.usuario.username} — {self.partido}"
    
class Mensaje(models.Model):
    usuario   = models.ForeignKey(User, on_delete=models.CASCADE)
    texto     = models.CharField(max_length=300)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.usuario.username}: {self.texto[:50]}"

class Desafio(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aceptado',  'Aceptado'),
        ('rechazado', 'Rechazado'),
    ]

    retador      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='desafios_enviados')
    retado       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='desafios_recibidos')
    partido      = models.ForeignKey(Partido, on_delete=models.CASCADE)
    monto        = models.IntegerField(default=0)
    gl_retador   = models.IntegerField(null=True, blank=True)
    gv_retador   = models.IntegerField(null=True, blank=True)
    gl_retado    = models.IntegerField(null=True, blank=True)
    gv_retado    = models.IntegerField(null=True, blank=True)
    estado       = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pendiente')
    creado_en    = models.DateTimeField(auto_now_add=True)

    def resultado_retador(self):
        if self.gl_retador is None or self.gv_retador is None:
            return None
        if self.gl_retador > self.gv_retador: return 'L'
        if self.gl_retador < self.gv_retador: return 'V'
        return 'E'

    def resultado_retado(self):
        if self.gl_retado is None or self.gv_retado is None:
            return None
        if self.gl_retado > self.gv_retado: return 'L'
        if self.gl_retado < self.gv_retado: return 'V'
        return 'E'

    def ganador(self):
        if not self.partido.jugado or self.estado != 'aceptado':
            return None
        real = self.partido.resultado_real()
        if real is None:
            return None
        pred_retador = self.resultado_retador()
        pred_retado  = self.resultado_retado()
        exacto_retador = (self.gl_retador == self.partido.goles_l and
                          self.gv_retador == self.partido.goles_v)
        exacto_retado  = (self.gl_retado == self.partido.goles_l and
                          self.gv_retado == self.partido.goles_v)
        pts_retador = 3 if exacto_retador else (1 if pred_retador == real else 0)
        pts_retado  = 3 if exacto_retado  else (1 if pred_retado  == real else 0)
        if pts_retador > pts_retado:
            return self.retador
        if pts_retado > pts_retador:
            return self.retado
        return None  # empate

    def __str__(self):
        return f"{self.retador} vs {self.retado} — {self.partido}"

    class Meta:
        ordering = ['-creado_en']
        
        
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    ultima_visita_chat = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"