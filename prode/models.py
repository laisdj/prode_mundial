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
    en_vivo = models.BooleanField(default=False)

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
    ganador_penales = models.CharField(max_length=50, blank=True, default='')

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
    partido      = models.ForeignKey(Partido, on_delete=models.CASCADE, null=True, blank=True)
    monto        = models.IntegerField(default=0)
    gl_retador   = models.IntegerField(null=True, blank=True)
    gv_retador   = models.IntegerField(null=True, blank=True)
    gl_retado    = models.IntegerField(null=True, blank=True)
    gv_retado    = models.IntegerField(null=True, blank=True)
    estado       = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pendiente')
    creado_en    = models.DateTimeField(auto_now_add=True)
    pagado = models.BooleanField(default=False)
    partido_elim = models.ForeignKey(PartidoEliminatorio, on_delete=models.CASCADE, null=True, blank=True)

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

    def get_partido(self):
        return self.partido or self.partido_elim

    def ganador(self):
        p = self.get_partido()
        if not p or not p.jugado or self.estado != 'aceptado':
            return None
        exacto_retador = (self.gl_retador == p.goles_l and self.gv_retador == p.goles_v)
        exacto_retado  = (self.gl_retado == p.goles_l and self.gv_retado == p.goles_v)
        if exacto_retador and not exacto_retado:
            return self.retador
        if exacto_retado and not exacto_retador:
            return self.retado
        return None

    def __str__(self):
        return f"{self.retador} vs {self.retado} — {self.partido}"

    class Meta:
        ordering = ['-creado_en']
        
        
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    ultima_visita_chat = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"
    
class VotoDesafio(models.Model):
    VOTO_CHOICES = [
        ('1', 'Gana retador'),
        ('2', 'Gana retado'),
        ('0', 'Empate'),
    ]
    desafio  = models.ForeignKey(Desafio, on_delete=models.CASCADE, related_name='votos')
    usuario  = models.ForeignKey(User, on_delete=models.CASCADE)
    voto     = models.CharField(max_length=1, choices=VOTO_CHOICES)
    comentario = models.CharField(max_length=200, blank=True, default='')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('desafio', 'usuario')

    def __str__(self):
        return f"{self.usuario.username} vota {self.voto} en {self.desafio}"