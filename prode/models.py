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