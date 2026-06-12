import requests
from django.core.management.base import BaseCommand
from prode.models import Partido

TEAM_MAP = {
    'Mexico':          'México',
    'South Africa':    'Sudáfrica',
    'South Korea':     'Corea del Sur',
    'Czech Republic':  'Chequia',
    'Czechia':         'Chequia',
    'Canada':          'Canadá',
    'Bosnia':          'Bosnia',
    'USA':             'EE.UU.',
    'United States':   'EE.UU.',
    'Qatar':           'Qatar',
    'Switzerland':     'Suiza',
    'Brazil':          'Brasil',
    'Morocco':         'Marruecos',
    'Haiti':           'Haití',
    'Scotland':        'Escocia',
    'Australia':       'Australia',
    'Turkey':          'Turquía',
    'Turkiye':         'Turquía',
    'Germany':         'Alemania',
    'Curacao':         'Curazao',
    'Curaçao':         'Curazao',
    'Netherlands':     'Países Bajos',
    'Japan':           'Japón',
    'Ivory Coast':     'Costa de Marfil',
    "Cote d'Ivoire":   'Costa de Marfil',
    'Ecuador':         'Ecuador',
    'Sweden':          'Suecia',
    'Tunisia':         'Túnez',
    'Spain':           'España',
    'Cape Verde':      'Cabo Verde',
    'Belgium':         'Bélgica',
    'Egypt':           'Egipto',
    'Saudi Arabia':    'Arabia Saudita',
    'Uruguay':         'Uruguay',
    'Iran':            'Irán',
    'New Zealand':     'Nueva Zelanda',
    'France':          'Francia',
    'Senegal':         'Senegal',
    'Iraq':            'Irak',
    'Norway':          'Noruega',
    'Argentina':       'Argentina',
    'Algeria':         'Argelia',
    'Austria':         'Austria',
    'Jordan':          'Jordania',
    'Portugal':        'Portugal',
    'DR Congo':        'R.D. Congo',
    'Congo DR':        'R.D. Congo',
    'England':         'Inglaterra',
    'Croatia':         'Croacia',
    'Ghana':           'Ghana',
    'Panama':          'Panamá',
    'Uzbekistan':      'Uzbekistán',
    'Colombia':        'Colombia',
    'Paraguay':        'Paraguay',
}


class Command(BaseCommand):
    help = 'Actualiza resultados desde worldcup26.ir'

    def handle(self, *args, **kwargs):
        try:
            resp = requests.get('https://worldcup26.ir/get/games', timeout=10)
            resp.raise_for_status()
        except Exception as e:
            self.stderr.write(f'Error consultando API: {e}')
            return

        games = resp.json().get('games', [])
        actualizados = 0

        for g in games:
            if g.get('type') != 'group':
                continue

            time_elapsed = g.get('time_elapsed', '')
            finished = g.get('finished', '').upper()
            en_vivo = time_elapsed in ('live', '1H', '2H', 'HT', 'ET', 'P')
            terminado = time_elapsed in ('finished', 'FT') or finished == 'TRUE'
            if not en_vivo and not terminado:
                continue

            home_en = g.get('home_team_name_en', '')
            away_en = g.get('away_team_name_en', '')
            home = TEAM_MAP.get(home_en, home_en)
            away = TEAM_MAP.get(away_en, away_en)

            try:
                gl = int(g.get('home_score', 0))
                gv = int(g.get('away_score', 0))
            except (ValueError, TypeError):
                continue

            try:
                partido = Partido.objects.get(local=home, visita=away)
                partido.goles_l = gl
                partido.goles_v = gv
                partido.jugado = terminado  # solo marca jugado si terminó
                partido.en_vivo = en_vivo
                partido.save()
                actualizados += 1
            except Partido.DoesNotExist:
                self.stderr.write(f'No encontrado: {home} vs {away}')

        self.stdout.write(f'{actualizados} partidos actualizados.')