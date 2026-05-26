import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from prode.models import Partido

TEAM_MAP = {
    'Mexico':                 'México',
    'South Africa':           'Sudáfrica',
    'Korea Republic':         'Corea del Sur',
    'Czechia':                'Chequia',
    'Canada':                 'Canadá',
    'Bosnia and Herzegovina': 'Bosnia',
    'USA':                    'EE.UU.',
    'Paraguay':               'Paraguay',
    'Qatar':                  'Qatar',
    'Switzerland':            'Suiza',
    'Brazil':                 'Brasil',
    'Morocco':                'Marruecos',
    'Haiti':                  'Haití',
    'Scotland':               'Escocia',
    'Australia':              'Australia',
    'Türkiye':                'Turquía',
    'Germany':                'Alemania',
    'Curaçao':                'Curazao',
    'Netherlands':            'Países Bajos',
    'Japan':                  'Japón',
    "Côte d'Ivoire":          'Costa de Marfil',
    'Ecuador':                'Ecuador',
    'Sweden':                 'Suecia',
    'Tunisia':                'Túnez',
    'Spain':                  'España',
    'Cape Verde':             'Cabo Verde',
    'Belgium':                'Bélgica',
    'Egypt':                  'Egipto',
    'Saudi Arabia':           'Arabia Saudita',
    'Uruguay':                'Uruguay',
    'Iran':                   'Irán',
    'New Zealand':            'Nueva Zelanda',
    'France':                 'Francia',
    'Senegal':                'Senegal',
    'Iraq':                   'Irak',
    'Norway':                 'Noruega',
    'Argentina':              'Argentina',
    'Algeria':                'Argelia',
    'Austria':                'Austria',
    'Jordan':                 'Jordania',
    'Portugal':               'Portugal',
    'DR Congo':               'R.D. Congo',
    'England':                'Inglaterra',
    'Croatia':                'Croacia',
    'Ghana':                  'Ghana',
    'Panama':                 'Panamá',
    'Uzbekistan':             'Uzbekistán',
    'Colombia':               'Colombia',
}


class Command(BaseCommand):
    help = 'Actualiza resultados reales desde football-data.org'

    def handle(self, *args, **kwargs):
        token = settings.FOOTBALL_API_TOKEN
        url = 'https://api.football-data.org/v4/competitions/WC/matches?season=2026'
        headers = {'X-Auth-Token': token}

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            self.stderr.write(f'Error consultando API: {e}')
            return

        matches = resp.json().get('matches', [])
        actualizados = 0

        for m in matches:
            if m.get('stage') != 'GROUP_STAGE':
                continue
            if m.get('status') != 'FINISHED':
                continue

            home_api = m['homeTeam']['name']
            away_api = m['awayTeam']['name']
            home = TEAM_MAP.get(home_api, home_api)
            away = TEAM_MAP.get(away_api, away_api)
            gl = m['score']['fullTime']['home']
            gv = m['score']['fullTime']['away']

            if gl is None or gv is None:
                continue

            try:
                partido = Partido.objects.get(local=home, visita=away)
                partido.goles_l = gl
                partido.goles_v = gv
                partido.jugado = True
                partido.save()
                actualizados += 1
            except Partido.DoesNotExist:
                self.stderr.write(f'No encontrado: {home} vs {away}')

        self.stdout.write(f'{actualizados} partidos actualizados.')