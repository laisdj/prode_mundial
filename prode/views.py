from .models import Partido, Pronostico, PartidoEliminatorio, PronosticoEliminatorio, Mensaje, Desafio, PerfilUsuario
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import Partido, Pronostico, PartidoEliminatorio, PronosticoEliminatorio
from datetime import date
from .models import Partido, Pronostico, PartidoEliminatorio, PronosticoEliminatorio, Mensaje
from .models import Partido, Pronostico, PartidoEliminatorio, PronosticoEliminatorio, Mensaje, Desafio, PerfilUsuario, VotoDesafio, PrediccionPodio

def login_view(request):
    if request.user.is_authenticated:
        return redirect('ranking')
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('pronosticos')
        messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'prode/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def registro(request):
    if request.method == 'POST':
        username = request.POST['username'].strip()
        password = request.POST['password']
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Ese nombre de usuario ya existe.')
        else:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect('pronosticos')
    return render(request, 'prode/registro.html')

def partidos(request):
    todos = Partido.objects.all()

    todos_prons = {}
    for pron in Pronostico.objects.select_related('usuario', 'partido').all():
        if pron.partido_id not in todos_prons:
            todos_prons[pron.partido_id] = []
        todos_prons[pron.partido_id].append(pron)

    mi_pron = {}
    if request.user.is_authenticated:
        for pron in Pronostico.objects.filter(usuario=request.user).select_related('partido'):
            mi_pron[pron.partido_id] = pron

    partidos_ctx = []
    for p in todos:
        prons_partido = todos_prons.get(p.id, [])
        plenos = []
        resultados = []
        for pron in prons_partido:
            pts = pron.puntos()
            inicial = pron.usuario.username[:2].capitalize()
            if pts == 3:
                plenos.append(inicial)
            elif pts == 1:
                resultados.append(inicial)

        mi = mi_pron.get(p.id)
        mi_pred = f"{mi.goles_l}-{mi.goles_v}" if mi else None
        mi_pts = mi.puntos() if mi else None

        partidos_ctx.append({
            'partido': p,
            'plenos': plenos,
            'resultados': resultados,
            'mi_pred': mi_pred,
            'mi_pts': mi_pts,
        })

    return render(request, 'prode/partidos.html', {'partidos': partidos_ctx})

def ranking(request):
    usuarios = User.objects.filter(is_superuser=False)
    usuarios_f2 = usuarios.exclude(username='Rodrigo Walker')

    try:
        final = PartidoEliminatorio.objects.get(ronda='FIN', jugado=True)
        campeon = final.local if final.goles_l > final.goles_v else final.visita
        subcampeon = final.visita if final.goles_l > final.goles_v else final.local
    except PartidoEliminatorio.DoesNotExist:
        campeon = subcampeon = None

    try:
        tercero_partido = PartidoEliminatorio.objects.get(ronda='3PL', jugado=True)
        tercero = tercero_partido.local if tercero_partido.goles_l > tercero_partido.goles_v else tercero_partido.visita
        cuarto = tercero_partido.visita if tercero_partido.goles_l > tercero_partido.goles_v else tercero_partido.local
    except PartidoEliminatorio.DoesNotExist:
        tercero = cuarto = None

    partidos_con_resultado = Partido.objects.filter(jugado=True).count()
    partidos_elim_jugados = PartidoEliminatorio.objects.filter(jugado=True).count()

    tabla_f1 = []
    tabla_f2 = []

    for u in usuarios:
        prons_f1 = Pronostico.objects.filter(usuario=u).select_related('partido')
        pts_f1 = sum(p.puntos() for p in prons_f1)
        exactos_f1 = sum(1 for p in prons_f1 if p.puntos() == 3)
        resultados_f1 = sum(1 for p in prons_f1 if p.puntos() == 1)
        pct = round((pts_f1 / (partidos_con_resultado * 3)) * 100) if partidos_con_resultado > 0 else 0

        tabla_f1.append({
            'usuario': u,
            'exactos_f1': exactos_f1,
            'resultados_f1': resultados_f1,
            'pts_f1': pts_f1,
            'pct': pct,
        })

        if u.username == 'Rodrigo Walker':
            continue

        prons_f2 = PronosticoEliminatorio.objects.filter(usuario=u).select_related('partido')
        pts_f2 = sum(p.puntos() for p in prons_f2)
        exactos_f2 = sum(1 for p in prons_f2 if p.puntos() == 3)
        resultados_f2 = sum(1 for p in prons_f2 if p.puntos() == 1)
        pct_f2 = round((pts_f2 / (partidos_elim_jugados * 3)) * 100) if partidos_elim_jugados > 0 else 0

        bonus = 0
        try:
            podio = PrediccionPodio.objects.get(usuario=u)
            if campeon and podio.primero == campeon:
                bonus += 5
            if subcampeon and podio.segundo == subcampeon:
                bonus += 3
            if tercero and podio.tercero == tercero:
                bonus += 2
            if cuarto and podio.cuarto == cuarto:
                bonus += 1
        except PrediccionPodio.DoesNotExist:
            pass

        total_f2 = pts_f2 + bonus

        tabla_f2.append({
            'usuario': u,
            'exactos_f2': exactos_f2,
            'resultados_f2': resultados_f2,
            'pts_f2': pts_f2,
            'pct_f2': pct_f2,
            'bonus': bonus,
            'total_f2': total_f2,
        })

    tabla_f1.sort(key=lambda x: x['pts_f1'], reverse=True)
    tabla_f2.sort(key=lambda x: x['total_f2'], reverse=True)

    tabla_acumulada = []
    for row1 in tabla_f1:
        u = row1['usuario']
        row2 = next((r for r in tabla_f2 if r['usuario'] == u), None)
        pts_f1_val = row1['pts_f1']
        pts_f2_val = row2['pts_f2'] if row2 else 0
        bonus_val = row2['bonus'] if row2 else 0
        total_acum = pts_f1_val + pts_f2_val + bonus_val
        tabla_acumulada.append({
            'usuario': u,
            'pts_f1': pts_f1_val,
            'pts_f2': pts_f2_val,
            'bonus': bonus_val,
            'total_acum': total_acum,
        })
    tabla_acumulada.sort(key=lambda x: x['total_acum'], reverse=True)

    ranking_anterior = request.session.get('ranking_anterior', {})
    for i, row in enumerate(tabla_f2):
        pos_actual = i + 1
        pos_ant = ranking_anterior.get(row['usuario'].username)
        if pos_ant is None:
            row['flecha'] = '—'
        elif pos_actual < pos_ant:
            row['flecha'] = '⬆️'
        elif pos_actual > pos_ant:
            row['flecha'] = '⬇️'
        else:
            row['flecha'] = '➡️'

    request.session['ranking_anterior'] = {
        row['usuario'].username: i + 1
        for i, row in enumerate(tabla_f2)
    }

    partidos_jugados = Partido.objects.filter(jugado=True).count()
    total_partidos = Partido.objects.count()
    partidos_elim_total = 32
    partidos_elim_jugados_header = PartidoEliminatorio.objects.filter(jugado=True).count()

    progreso = []
    for u in usuarios:
        total_prons = Pronostico.objects.filter(usuario=u).count()
        progreso.append({
            'usuario': u,
            'completados': total_prons,
            'porcentaje': round((total_prons / 72) * 100),
        })
    progreso.sort(key=lambda x: x['porcentaje'], reverse=True)

    desafios_activos = Desafio.objects.filter(
        estado='aceptado'
    ).select_related('retador', 'retado', 'partido', 'partido_elim').order_by('-creado_en')

    desafios_ctx = []
    for d in desafios_activos:
        p = d.get_partido()
        if not p:
            continue
        g = d.ganador()
        votos = d.votos.all()
        comentarios = [v for v in votos if v.comentario]
        total_votos = votos.count()
        v1 = votos.filter(voto='1').count()
        v2 = votos.filter(voto='2').count()
        v0 = votos.filter(voto='0').count()
        desafios_ctx.append({
            'desafio': d,
            'partido_obj': p,
            'ganador': g,
            'empate': g is None and p.jugado,
            'pendiente': not p.jugado,
            'total_votos': total_votos,
            'pct1': round((v1/total_votos)*100) if total_votos else 0,
            'pct2': round((v2/total_votos)*100) if total_votos else 0,
            'pct0': round((v0/total_votos)*100) if total_votos else 0,
            'v1': v1, 'v2': v2, 'v0': v0,
            'comentarios': comentarios,
        })

    return render(request, 'prode/ranking.html', {
        'tabla_f1': tabla_f1,
        'tabla_f2': tabla_f2,
        'tabla_acumulada': tabla_acumulada,
        'partidos_jugados': partidos_jugados,
        'total_partidos': total_partidos,
        'partidos_elim_jugados_header': partidos_elim_jugados_header,
        'partidos_elim_total': partidos_elim_total,
        'progreso': progreso,
        'desafios': desafios_ctx,
    })


def clasificacion(request):
    grupos = {}
    for letra in 'ABCDEFGHIJKL':
        grupos[letra] = {}

    partidos_jugados = Partido.objects.filter(jugado=True)

    for p in partidos_jugados:
        g = p.grupo
        for equipo, gf, gc in [(p.local, p.goles_l, p.goles_v),
                                (p.visita, p.goles_v, p.goles_l)]:
            if equipo not in grupos[g]:
                grupos[g][equipo] = {'pj':0,'g':0,'e':0,'p':0,'gf':0,'gc':0}
            e = grupos[g][equipo]
            e['pj'] += 1
            e['gf'] += gf
            e['gc'] += gc
            if gf > gc:
                e['g'] += 1
            elif gf == gc:
                e['e'] += 1
            else:
                e['p'] += 1

    todos = Partido.objects.all()
    for p in todos:
        for equipo in [p.local, p.visita]:
            if equipo not in grupos[p.grupo]:
                grupos[p.grupo][equipo] = {'pj':0,'g':0,'e':0,'p':0,'gf':0,'gc':0}

    grupos_ordenados = {}
    terceros = []

    for letra, equipos in grupos.items():
        tabla = []
        for nombre, stats in equipos.items():
            stats['pts'] = stats['g'] * 3 + stats['e']
            stats['dg'] = stats['gf'] - stats['gc']
            stats['nombre'] = nombre
            stats['estado'] = ''
            tabla.append(stats)
        tabla.sort(key=lambda x: (-x['pts'], -x['dg'], -x['gf']))
        grupos_ordenados[letra] = tabla
        if len(tabla) >= 3:
            t = tabla[2].copy()
            t['grupo'] = letra
            terceros.append(t)

    terceros.sort(key=lambda x: (-x['pts'], -x['dg'], -x['gf']))
    mejores_terceros = set(t['nombre'] for t in terceros[:8])

    for letra, tabla in grupos_ordenados.items():
        for i, e in enumerate(tabla):
            if i == 0 or i == 1:
                e['estado'] = 'directo'
            elif i == 2 and e['nombre'] in mejores_terceros:
                e['estado'] = 'posible'
            else:
                e['estado'] = ''

    return render(request, 'prode/clasificacion.html', {'grupos': grupos_ordenados})

@login_required(login_url='login')
def mi_clasificacion(request):
    FIFA_RANKING = {
        'Francia': 1, 'España': 2, 'Argentina': 3, 'Inglaterra': 4,
        'Portugal': 5, 'Brasil': 6, 'Países Bajos': 7, 'Marruecos': 8,
        'Bélgica': 9, 'Alemania': 10, 'Croacia': 11, 'Colombia': 13,
        'Senegal': 14, 'México': 15, 'EE.UU.': 16, 'Uruguay': 17,
        'Japón': 18, 'Suiza': 19, 'Irán': 21, 'Austria': 23,
        'Ecuador': 24, 'Corea del Sur': 25, 'Australia': 26,
        'Egipto': 29, 'Canadá': 30, 'Costa de Marfil': 33,
        'Qatar': 35, 'Argelia': 36, 'Suecia': 39, 'Túnez': 40,
        'Chequia': 41, 'Turquía': 42, 'Noruega': 44, 'Escocia': 47,
        'R.D. Congo': 51, 'Bosnia': 52, 'Panamá': 53,
        'Arabia Saudita': 57, 'Sudáfrica': 60, 'Irak': 61,
        'Uzbekistán': 62, 'Paraguay': 64, 'Ghana': 65,
        'Jordania': 68, 'Cabo Verde': 70, 'Curazao': 81,
        'Haití': 83, 'Nueva Zelanda': 95,
    }

    grupos = {}
    for letra in 'ABCDEFGHIJKL':
        grupos[letra] = {}

    mis_prons = Pronostico.objects.filter(
        usuario=request.user
    ).select_related('partido')

    for pron in mis_prons:
        p = pron.partido
        g = p.grupo
        if pron.goles_l is None or pron.goles_v is None:
            continue
        for equipo, gf, gc in [(p.local, pron.goles_l, pron.goles_v),
                                (p.visita, pron.goles_v, pron.goles_l)]:
            if equipo not in grupos[g]:
                grupos[g][equipo] = {'pj':0,'g':0,'e':0,'p':0,'gf':0,'gc':0}
            e = grupos[g][equipo]
            e['pj'] += 1
            e['gf'] += gf
            e['gc'] += gc
            if gf > gc:
                e['g'] += 1
            elif gf == gc:
                e['e'] += 1
            else:
                e['p'] += 1

    todos = Partido.objects.all()
    for p in todos:
        for equipo in [p.local, p.visita]:
            if equipo not in grupos[p.grupo]:
                grupos[p.grupo][equipo] = {'pj':0,'g':0,'e':0,'p':0,'gf':0,'gc':0}

    grupos_ordenados = {}
    terceros = []
    primeros = {}
    segundos = {}

    for letra, equipos in grupos.items():
        tabla = []
        for nombre, stats in equipos.items():
            stats['pts'] = stats['g'] * 3 + stats['e']
            stats['dg'] = stats['gf'] - stats['gc']
            stats['nombre'] = nombre
            stats['estado'] = ''
            stats['fifa'] = FIFA_RANKING.get(nombre, 999)
            tabla.append(stats)
        tabla.sort(key=lambda x: (-x['pts'], -x['dg'], -x['gf'], x['fifa']))
        grupos_ordenados[letra] = tabla

        if len(tabla) >= 1:
            primeros[letra] = tabla[0]['nombre']
        if len(tabla) >= 2:
            segundos[letra] = tabla[1]['nombre']
        if len(tabla) >= 3:
            t = tabla[2].copy()
            t['grupo'] = letra
            terceros.append(t)

    terceros.sort(key=lambda x: (-x['pts'], -x['dg'], -x['gf'], x['fifa']))
    mejores_8 = terceros[:8]
    mejores_terceros_nombres = set(t['nombre'] for t in mejores_8)
    mejor_tercero_por_grupo = {t['grupo']: t['nombre'] for t in mejores_8}

    for letra, tabla in grupos_ordenados.items():
        for i, e in enumerate(tabla):
            if i == 0 or i == 1:
                e['estado'] = 'directo'
            elif i == 2 and e['nombre'] in mejores_terceros_nombres:
                e['estado'] = 'posible'
            else:
                e['estado'] = ''

    def resolver_tercero(slot_grupos):
        grupos_validos = slot_grupos.replace(' ', '').split('/')
        for g in grupos_validos:
            if g in mejor_tercero_por_grupo:
                return mejor_tercero_por_grupo[g]
        return '3° ' + slot_grupos

    def eq(slot):
        if slot.startswith('1°'):
            return primeros.get(slot[2:], slot)
        elif slot.startswith('2°'):
            return segundos.get(slot[2:], slot)
        elif slot.startswith('3°'):
            return resolver_tercero(slot[2:].strip())
        return slot

    SLOTS_R32 = [
        (1,  '2°A',  '2°B'),
        (2,  '1°E',  '3° A/B/C/D/F'),
        (3,  '1°F',  '2°C'),
        (4,  '1°C',  '2°F'),
        (5,  '1°I',  '3° C/D/F/G/H'),
        (6,  '2°E',  '2°I'),
        (7,  '1°A',  '3° C/E/F/H/I'),
        (8,  '1°L',  '3° E/H/I/J/K'),
        (9,  '1°D',  '3° B/E/F/I/J'),
        (10, '1°G',  '3° A/E/H/I/J'),
        (11, '2°K',  '2°L'),
        (12, '1°H',  '2°J'),
        (13, '1°B',  '3° E/F/G/I/J'),
        (14, '1°J',  '2°H'),
        (15, '1°K',  '3° D/E/I/J/L'),
        (16, '2°D',  '2°G'),
    ]

    cruces_r32 = []
    for orden, slot_l, slot_v in SLOTS_R32:
        cruces_r32.append({
            'orden': orden,
            'slot_local': slot_l,
            'slot_visita': slot_v,
            'local': eq(slot_l),
            'visita': eq(slot_v),
        })

    cruces_izq = [c for c in cruces_r32 if c['orden'] <= 8]
    cruces_der = [c for c in cruces_r32 if c['orden'] >= 9]

    return render(request, 'prode/mi_clasificacion.html', {
        'grupos': grupos_ordenados,
        'cruces_r32': cruces_r32,
        'cruces_izq': cruces_izq,
        'cruces_der': cruces_der,
    })


@login_required(login_url='login')
def pronosticos(request):
    if request.user.is_staff:
        return redirect('ranking')

    hoy = date.today()
    cierre = date(2026, 6, 8)
    abierto = hoy <= cierre

    partidos = Partido.objects.all()

    if request.method == 'POST' and abierto:
        for partido in partidos:
            gl = request.POST.get(f'gl_{partido.id}', '').strip()
            gv = request.POST.get(f'gv_{partido.id}', '').strip()
            nota = request.POST.get(f'nota_{partido.id}', '').strip()

            if gl == '' and gv == '':
                Pronostico.objects.filter(
                    usuario=request.user, partido=partido
                ).delete()
            elif gl == '' or gv == '':
                pass
            else:
                try:
                    gl_int = int(gl)
                    gv_int = int(gv)
                    if gl_int < 0 or gv_int < 0:
                        continue
                    Pronostico.objects.update_or_create(
                        usuario=request.user,
                        partido=partido,
                        defaults={
                            'goles_l': gl_int,
                            'goles_v': gv_int,
                            'nota': nota,
                        }
                    )
                except ValueError:
                    pass
        messages.success(request, '¡Pronósticos guardados!')
        return redirect('pronosticos')

    mis_prons = {
        p.partido_id: p
        for p in Pronostico.objects.filter(usuario=request.user)
    }
    partidos_ctx = []
    for p in partidos:
        pron = mis_prons.get(p.id)
        partidos_ctx.append({
            'partido': p,
            'gl': pron.goles_l if pron else None,
            'gv': pron.goles_v if pron else None,
            'nota': pron.nota if pron else '',
            'pts': pron.puntos() if pron else None,
        })

    return render(request, 'prode/pronosticos.html', {
        'partidos': partidos_ctx,
        'abierto': abierto,
    })


from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def cargar_resultados(request):
    partidos = Partido.objects.all()

    if request.method == 'POST':
        for partido in partidos:
            gl = request.POST.get(f'gl_{partido.id}', '').strip()
            gv = request.POST.get(f'gv_{partido.id}', '').strip()
            jugado = request.POST.get(f'jugado_{partido.id}')
            if gl != '' and gv != '':
                try:
                    partido.goles_l = int(gl)
                    partido.goles_v = int(gv)
                    partido.jugado = True
                    partido.save()
                except ValueError:
                    pass
            elif gl == '' and gv == '':
                partido.goles_l = None
                partido.goles_v = None
                partido.jugado = False
                partido.save()
        messages.success(request, 'Resultados guardados.')
        return redirect('cargar_resultados')

    return render(request, 'prode/cargar_resultados.html', {'partidos': partidos})


@staff_member_required
def cargar_equipos_eliminatoria(request):
    partidos = PartidoEliminatorio.objects.filter(ronda='R32').order_by('orden')

    if request.method == 'POST':
        for partido in partidos:
            local = request.POST.get(f'local_{partido.id}', '').strip()
            visita = request.POST.get(f'visita_{partido.id}', '').strip()
            fecha_str = request.POST.get(f'fecha_{partido.id}', '').strip()
            if fecha_str:
                import datetime
                from django.utils import timezone
                try:
                    dt = datetime.datetime.strptime(fecha_str, '%Y-%m-%dT%H:%M')
                    partido.fecha = timezone.make_aware(dt)
                except ValueError:
                    pass
            partido.local = local
            partido.visita = visita
            partido.save()
        messages.success(request, 'Equipos actualizados.')
        return redirect('cargar_equipos_eliminatoria')

    return render(request, 'prode/cargar_equipos_eliminatoria.html', {'partidos': partidos})


@staff_member_required
def cargar_resultados_eliminatoria(request):
    partidos = PartidoEliminatorio.objects.all().order_by('orden')

    if request.method == 'POST':
        for partido in partidos:
            gl = request.POST.get(f'gl_{partido.id}', '').strip()
            gv = request.POST.get(f'gv_{partido.id}', '').strip()
            jugado = request.POST.get(f'jugado_{partido.id}')
            pl = request.POST.get(f'pl_{partido.id}', '').strip()
            pv = request.POST.get(f'pv_{partido.id}', '').strip()

            if gl != '' and gv != '':
                try:
                    partido.goles_l = int(gl)
                    partido.goles_v = int(gv)
                    partido.jugado = jugado == True
                    partido.penales_l = int(pl) if pl != '' else None
                    partido.penales_v = int(pv) if pv != '' else None
                    partido.save()
                except ValueError:
                    pass
            elif gl == '' and gv == '':
                partido.goles_l = None
                partido.goles_v = None
                partido.penales_l = None
                partido.penales_v = None
                partido.jugado = False
                partido.save()
        messages.success(request, 'Resultados eliminatoria guardados.')
        return redirect('cargar_resultados_eliminatoria')

    return render(request, 'prode/cargar_resultados_eliminatoria.html', {'partidos': partidos})


@login_required(login_url='login')
def pronosticos_eliminatoria(request):
    if request.user.is_staff:
        return redirect('ranking')
    if not settings.FASE2_ACTIVA:
        return redirect('ranking')

    from django.utils import timezone
    from datetime import datetime as dt_class

    limite_podio = timezone.make_aware(dt_class(2026, 6, 30, 10, 0))

    partidos = PartidoEliminatorio.objects.all().order_by('fecha')
    partidos_con_equipos = [p for p in partidos if p.local and p.visita]

    mi_podio, _ = PrediccionPodio.objects.get_or_create(usuario=request.user)
    podio_bloqueado = timezone.now() >= limite_podio

    equipos_r32 = set()
    for p in PartidoEliminatorio.objects.filter(ronda='R32'):
        if p.local:
            equipos_r32.add(p.local)
        if p.visita:
            equipos_r32.add(p.visita)
    equipos_r32 = sorted(equipos_r32)

    if request.method == 'POST':
        if 'guardar_podio' in request.POST and not podio_bloqueado:
            mi_podio.primero = request.POST.get('primero', '').strip()
            mi_podio.segundo = request.POST.get('segundo', '').strip()
            mi_podio.tercero = request.POST.get('tercero', '').strip()
            mi_podio.cuarto  = request.POST.get('cuarto', '').strip()
            mi_podio.save()
            messages.success(request, '¡Podio guardado!')
            return redirect('pronosticos_eliminatoria')

        for partido in partidos_con_equipos:
            if partido.fecha and timezone.now() >= partido.fecha:
                continue

            gl = request.POST.get(f'gl_{partido.id}', '').strip()
            gv = request.POST.get(f'gv_{partido.id}', '').strip()
            ganador_empate = request.POST.get(f'gan_{partido.id}', '').strip()

            if gl == '' or gv == '':
                PronosticoEliminatorio.objects.filter(
                    usuario=request.user, partido=partido
                ).delete()
            else:
                try:
                    gl_int = int(gl)
                    gv_int = int(gv)
                    if gl_int < 0 or gv_int < 0:
                        continue
                    PronosticoEliminatorio.objects.update_or_create(
                        usuario=request.user,
                        partido=partido,
                        defaults={
                            'goles_l': gl_int,
                            'goles_v': gv_int,
                            'local': partido.local,
                            'visita': partido.visita,
                            'ganador_penales': ganador_empate if gl_int == gv_int else '',
                        }
                    )
                except ValueError:
                    pass
        messages.success(request, '¡Pronósticos guardados!')
        return redirect('pronosticos_eliminatoria')

    mis_prons = {
        p.partido_id: p
        for p in PronosticoEliminatorio.objects.filter(usuario=request.user)
    }

    todos_prons = {}
    for pron in PronosticoEliminatorio.objects.select_related('usuario', 'partido').all():
        if pron.partido_id not in todos_prons:
            todos_prons[pron.partido_id] = []
        todos_prons[pron.partido_id].append(pron)

    rondas = {
        'R32': 'Round of 32',
        'R16': 'Round of 16',
        'QF':  'Cuartos de final',
        'SF':  'Semifinal',
        '3PL': 'Tercer y cuarto lugar',
        'FIN': 'Final',
    }

    partidos_ctx = []
    for p in partidos_con_equipos:
        pron = mis_prons.get(p.id)

        prons_partido = todos_prons.get(p.id, [])
        plenos = []
        resultados = []
        for otro_pron in prons_partido:
            pts = otro_pron.puntos()
            inicial = otro_pron.usuario.username[:2].capitalize()
            if pts == 3:
                plenos.append(inicial)
            elif pts == 1:
                resultados.append(inicial)

        bloqueado = bool(p.fecha and timezone.now() >= p.fecha)

        partidos_ctx.append({
            'partido': p,
            'ronda_nombre': rondas.get(p.ronda, p.ronda),
            'gl': pron.goles_l if pron else None,
            'gv': pron.goles_v if pron else None,
            'ganador_penales': pron.ganador_penales if pron else '',
            'pts': pron.puntos() if pron else None,
            'plenos': plenos,
            'resultados': resultados,
            'bloqueado': bloqueado,
        })

    return render(request, 'prode/pronosticos_eliminatoria.html', {
        'partidos': partidos_ctx,
        'equipos_r32': equipos_r32,
        'mi_podio': mi_podio,
        'podio_bloqueado': podio_bloqueado,
    })


def bracket(request):
    partidos = PartidoEliminatorio.objects.all()

    def ganador(p):
        if not p.jugado:
            return None
        r = p.resultado_real()
        return p.local if r == 'L' else p.visita

    def fmt(p):
        return {
            'id': p.id,
            'local': p.local or p.slot_local,
            'visita': p.visita or p.slot_visita,
            'gl': p.goles_l,
            'gv': p.goles_v,
            'jugado': p.jugado,
            'ganador': ganador(p),
            'fecha': p.fecha,
        }

    # Orden visual fijo del bracket (izquierda 1-8, derecha 9-16)
    ORDEN_VISUAL_R32 = [
        ('Alemania', 'Paraguay'),
        ('Francia', 'Suecia'),
        ('Sudáfrica', 'Canadá'),
        ('Países Bajos', 'Marruecos'),
        ('Portugal', 'Croacia'),
        ('España', 'Austria'),
        ('EE.UU.', 'Bosnia'),
        ('Bélgica', 'Senegal'),
        ('Brasil', 'Japón'),
        ('Costa de Marfil', 'Noruega'),
        ('México', 'Ecuador'),
        ('Inglaterra', 'R.D. Congo'),
        ('Argentina', 'Cabo Verde'),
        ('Suiza', 'Argelia'),
        ('Colombia', 'Ghana'),
        ('Australia', 'Egipto'),
    ]

    r32_partidos = list(partidos.filter(ronda='R32'))
    r32 = {}
    for idx, (loc, vis) in enumerate(ORDEN_VISUAL_R32, start=1):
        encontrado = None
        for p in r32_partidos:
            if (p.local == loc and p.visita == vis) or (p.local == vis and p.visita == loc):
                encontrado = p
                break
        if encontrado:
            r32[idx] = fmt(encontrado)

    r16 = {p.id: fmt(p) for i, p in enumerate(partidos.filter(ronda='R16').order_by('fecha'), start=1)}
    r16 = {i+1: fmt(p) for i, p in enumerate(partidos.filter(ronda='R16').order_by('fecha'))}
    qf  = {i+1: fmt(p) for i, p in enumerate(partidos.filter(ronda='QF').order_by('fecha'))}
    sf  = {i+1: fmt(p) for i, p in enumerate(partidos.filter(ronda='SF').order_by('fecha'))}
    fin = partidos.filter(ronda='FIN').first()
    tpl = partidos.filter(ronda='3PL').first()

    ctx = {
        'r32': r32,
        'r16': r16,
        'qf':  qf,
        'sf':  sf,
        'fin': fmt(fin) if fin else None,
        'tpl': fmt(tpl) if tpl else None,
    }
    return render(request, 'prode/bracket.html', ctx)



@staff_member_required
def gestionar_eliminatoria(request):
    RONDAS = [
        ('R32', 'Round of 32'),
        ('R16', 'Round of 16'),
        ('QF',  'Cuartos de final'),
        ('SF',  'Semifinal'),
        ('3PL', 'Tercer y cuarto lugar'),
        ('FIN', 'Final'),
    ]

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'agregar':
            ronda = request.POST.get('ronda')
            local = request.POST.get('local', '').strip()
            visita = request.POST.get('visita', '').strip()
            slot_local = request.POST.get('slot_local', '').strip()
            slot_visita = request.POST.get('slot_visita', '').strip()

            fecha_str = request.POST.get('fecha', '').strip()
            fecha_dt = None
            if fecha_str:
                import datetime
                from django.utils import timezone
                try:
                    dt = datetime.datetime.strptime(fecha_str, '%Y-%m-%dT%H:%M')
                    fecha_dt = timezone.make_aware(dt)
                except ValueError:
                    pass

            if ronda and (local or slot_local) and (visita or slot_visita):
                PartidoEliminatorio.objects.create(
                    ronda=ronda,
                    slot_local=slot_local or local,
                    slot_visita=slot_visita or visita,
                    local=local,
                    visita=visita,
                    fecha=fecha_dt,
                    orden=PartidoEliminatorio.objects.count() + 1,
                )
                messages.success(request, f'Partido agregado al {dict(RONDAS).get(ronda)}.')

        elif accion == 'editar':
            partido_id = request.POST.get('partido_id')
            try:
                partido = PartidoEliminatorio.objects.get(id=partido_id)
                partido.local  = request.POST.get(f'local_{partido_id}', '').strip()
                partido.visita = request.POST.get(f'visita_{partido_id}', '').strip()
                fecha_str = request.POST.get(f'fecha_{partido_id}', '').strip()
                if fecha_str:
                    import datetime
                    from django.utils import timezone
                    try:
                        dt = datetime.datetime.strptime(fecha_str, '%Y-%m-%dT%H:%M')
                        partido.fecha = timezone.make_aware(dt)
                    except ValueError:
                        pass
                gl = request.POST.get(f'gl_{partido_id}', '').strip()
                gv = request.POST.get(f'gv_{partido_id}', '').strip()
                jugado = request.POST.get(f'jugado_{partido_id}')
                pl = request.POST.get(f'pl_{partido_id}', '').strip()
                pv = request.POST.get(f'pv_{partido_id}', '').strip()
                if gl != '' and gv != '':
                    partido.goles_l = int(gl)
                    partido.goles_v = int(gv)
                    partido.jugado = True
                    partido.penales_l = int(pl) if pl else None
                    partido.penales_v = int(pv) if pv else None
                else:
                    partido.goles_l = None
                    partido.goles_v = None
                    partido.jugado = False
                    partido.penales_l = None
                    partido.penales_v = None
                partido.save()
                messages.success(request, 'Partido actualizado.')
            except PartidoEliminatorio.DoesNotExist:
                pass

        elif accion == 'eliminar':
            partido_id = request.POST.get('partido_id')
            PartidoEliminatorio.objects.filter(id=partido_id).delete()
            messages.success(request, 'Partido eliminado.')

        return redirect('gestionar_eliminatoria')

    partidos_por_ronda = {}
    for codigo, nombre in RONDAS:
        partidos_por_ronda[nombre] = PartidoEliminatorio.objects.filter(ronda=codigo).order_by('fecha')

    return render(request, 'prode/gestionar_eliminatoria.html', {
        'partidos_por_ronda': partidos_por_ronda,
        'rondas': RONDAS,
    })


@login_required(login_url='login')
def chat(request):
    from django.utils import timezone

    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        texto = request.POST.get('texto', '').strip()
        if texto and len(texto) <= 300:
            Mensaje.objects.create(usuario=request.user, texto=texto)
        perfil.ultima_visita_chat = timezone.now()
        perfil.save()
        return redirect('chat')

    perfil.ultima_visita_chat = timezone.now()
    perfil.save()

    mensajes = Mensaje.objects.select_related('usuario').all()[:100]
    return render(request, 'prode/chat.html', {'mensajes': mensajes})


@login_required(login_url='login')
def chat_mensajes(request):
    from django.http import JsonResponse
    mensajes = Mensaje.objects.select_related('usuario').all()[:100]
    data = [
        {
            'usuario': m.usuario.username,
            'texto': m.texto,
            'hora': m.creado_en.strftime('%d/%m %H:%M'),
        }
        for m in mensajes
    ]
    return JsonResponse({'mensajes': data})


@login_required(login_url='login')
def desafios(request):
    enviados = Desafio.objects.filter(retador=request.user).select_related('retado', 'partido')
    recibidos = Desafio.objects.filter(retado=request.user).select_related('retador', 'partido')
    usuarios = User.objects.filter(is_superuser=False).exclude(id=request.user.id)
    partidos = Partido.objects.filter(jugado=False).order_by('fecha')
    partidos_elim = PartidoEliminatorio.objects.filter(jugado=False, local__isnull=False).exclude(local='').order_by('orden')

    return render(request, 'prode/desafios.html', {
        'enviados': enviados,
        'recibidos': recibidos,
        'usuarios': usuarios,
        'partidos': partidos,
        'partidos_elim': partidos_elim,
    })


@login_required(login_url='login')
def crear_desafio(request):
    if request.method == 'POST':
        retado_id = request.POST.get('retado')
        partido_id = request.POST.get('partido')
        partido_elim_id = request.POST.get('partido_elim')
        monto = request.POST.get('monto', '0').strip()
        gl = request.POST.get('gl', '').strip()
        gv = request.POST.get('gv', '').strip()

        try:
            retado = User.objects.get(id=retado_id)
            gl_int = int(gl)
            gv_int = int(gv)
            monto_int = int(monto) if monto else 0

            partido = None
            partido_elim = None
            if partido_id:
                partido = Partido.objects.get(id=partido_id)
            elif partido_elim_id:
                partido_elim = PartidoEliminatorio.objects.get(id=partido_elim_id)

            if retado == request.user:
                messages.error(request, 'No puedes desafiarte a ti mismo.')
            elif (partido and partido.jugado) or (partido_elim and partido_elim.jugado):
                messages.error(request, 'Ese partido ya se jugó.')
            else:
                Desafio.objects.create(
                    retador=request.user,
                    retado=retado,
                    partido=partido,
                    partido_elim=partido_elim,
                    monto=monto_int,
                    gl_retador=gl_int,
                    gv_retador=gv_int,
                )
                messages.success(request, f'¡Desafío enviado a {retado.username}!')
        except (ValueError, User.DoesNotExist, Partido.DoesNotExist, PartidoEliminatorio.DoesNotExist):
            messages.error(request, 'Datos inválidos.')

    return redirect('desafios')


@login_required(login_url='login')
def responder_desafio(request, desafio_id):
    try:
        desafio = Desafio.objects.get(id=desafio_id, retado=request.user)
    except Desafio.DoesNotExist:
        messages.error(request, 'Desafío no encontrado.')
        return redirect('desafios')

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'rechazar':
            desafio.estado = 'rechazado'
            desafio.save()
            messages.success(request, 'Desafío rechazado.')

        elif accion == 'aceptar':
            gl = request.POST.get('gl', '').strip()
            gv = request.POST.get('gv', '').strip()
            try:
                desafio.gl_retado = int(gl)
                desafio.gv_retado = int(gv)
                desafio.estado = 'aceptado'
                desafio.save()
                messages.success(request, '¡Desafío aceptado!')
            except ValueError:
                messages.error(request, 'Ingresa un marcador válido.')

    return redirect('desafios')


@staff_member_required
def eliminar_usuario(request, usuario_id):
    if request.method == 'POST':
        try:
            u = User.objects.get(id=usuario_id, is_superuser=False)
            nombre = u.username
            u.delete()
            messages.success(request, f'Usuario {nombre} eliminado.')
        except User.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
    return redirect('ranking')


def historial_desafios(request):
    desafios = Desafio.objects.filter(
        estado='aceptado'
    ).select_related('retador', 'retado', 'partido', 'partido_elim').order_by('-creado_en')

    historial = []
    for d in desafios:
        p = d.get_partido()
        if not p:
            continue
        g = d.ganador()
        historial.append({
            'desafio': d,
            'partido_obj': p,
            'ganador': g,
            'empate': g is None and p.jugado,
        })

    return render(request, 'prode/historial_desafios.html', {'historial': historial})


@login_required(login_url='login')
def borrar_mensaje(request, mensaje_id):
    if request.method == 'POST':
        try:
            if request.user.is_staff:
                m = Mensaje.objects.get(id=mensaje_id)
            else:
                m = Mensaje.objects.get(id=mensaje_id, usuario=request.user)
            m.delete()
        except Mensaje.DoesNotExist:
            pass
    return redirect('chat')


@login_required(login_url='login')
def marcar_pagado(request, desafio_id):
    if request.method == 'POST':
        try:
            d = Desafio.objects.get(id=desafio_id)
            ganador = d.ganador()
            if request.user == ganador or request.user.is_staff:
                d.pagado = not d.pagado
                d.save()
        except Desafio.DoesNotExist:
            pass
    return redirect('historial_desafios')


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def api_actualizar(request):
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command('actualizar_resultados', stdout=out)
    return JsonResponse({'resultado': out.getvalue()})

@login_required(login_url='login')
def votar_desafio(request, desafio_id):
    if request.method == 'POST':
        try:
            desafio = Desafio.objects.get(id=desafio_id)
            voto = request.POST.get('voto')
            comentario = request.POST.get('comentario', '').strip()
            if voto in ('0', '1', '2'):
                VotoDesafio.objects.update_or_create(
                    desafio=desafio,
                    usuario=request.user,
                    defaults={'voto': voto, 'comentario': comentario}
                )
                messages.success(request, '¡Voto registrado!')
        except Desafio.DoesNotExist:
            pass
    return redirect('detalle_desafio', desafio_id=desafio_id)


def detalle_desafio(request, desafio_id):
    try:
        desafio = Desafio.objects.get(id=desafio_id)
    except Desafio.DoesNotExist:
        return redirect('desafios')

    votos = VotoDesafio.objects.filter(desafio=desafio).select_related('usuario')
    total_votos = votos.count()

    v1 = votos.filter(voto='1').count()
    v2 = votos.filter(voto='2').count()
    v0 = votos.filter(voto='0').count()

    pct1 = round((v1 / total_votos) * 100) if total_votos else 0
    pct2 = round((v2 / total_votos) * 100) if total_votos else 0
    pct0 = round((v0 / total_votos) * 100) if total_votos else 0

    mi_voto = None
    if request.user.is_authenticated:
        try:
            mi_voto = VotoDesafio.objects.get(desafio=desafio, usuario=request.user)
        except VotoDesafio.DoesNotExist:
            pass

    ganador = desafio.ganador()

    return render(request, 'prode/detalle_desafio.html', {
        'desafio': desafio,
        'votos': votos,
        'total_votos': total_votos,
        'v1': v1, 'v2': v2, 'v0': v0,
        'pct1': pct1, 'pct2': pct2, 'pct0': pct0,
        'mi_voto': mi_voto,
        'ganador': ganador,
    })
    
@login_required(login_url='login')
def borrar_desafio(request, desafio_id):
    if request.method == 'POST':
        try:
            d = Desafio.objects.get(id=desafio_id)
            if request.user == d.retador or request.user.is_staff:
                d.delete()
                messages.success(request, 'Desafío eliminado.')
        except Desafio.DoesNotExist:
            pass
    return redirect('desafios')

def reglas(request):
    hoy = date.today()
    cierre = date(2026, 6, 8)
    abierto = hoy <= cierre
    return render(request, 'prode/reglas.html', {'abierto': abierto})

@login_required(login_url='login')
def simulador_bracket(request):
    ORDEN_VISUAL_R32 = [
        ('Alemania', 'Paraguay'),
        ('Francia', 'Suecia'),
        ('Sudáfrica', 'Canadá'),
        ('Países Bajos', 'Marruecos'),
        ('Portugal', 'Croacia'),
        ('España', 'Austria'),
        ('EE.UU.', 'Bosnia'),
        ('Bélgica', 'Senegal'),
        ('Brasil', 'Japón'),
        ('Costa de Marfil', 'Noruega'),
        ('México', 'Ecuador'),
        ('Inglaterra', 'R.D. Congo'),
        ('Argentina', 'Cabo Verde'),
        ('Suiza', 'Argelia'),
        ('Colombia', 'Ghana'),
        ('Australia', 'Egipto'),
    ]

    return render(request, 'prode/simulador_bracket.html', {
        'partidos_r32': ORDEN_VISUAL_R32,
    })
    
    
@staff_member_required
def progreso_eliminatoria(request):
    usuarios = User.objects.filter(is_superuser=False)

    progreso = []
    for u in usuarios:
        tiene_podio = PrediccionPodio.objects.filter(
            usuario=u
        ).exclude(primero='').exists()

        prons_r32 = PronosticoEliminatorio.objects.filter(
            usuario=u, partido__ronda='R32'
        ).count()

        progreso.append({
            'usuario': u,
            'tiene_podio': tiene_podio,
            'prons_r32': prons_r32,
        })

    progreso.sort(key=lambda x: (x['tiene_podio'], x['prons_r32']))

    return render(request, 'prode/progreso_eliminatoria.html', {
        'progreso': progreso,
    })