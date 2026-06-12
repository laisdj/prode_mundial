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
from .models import Partido, Pronostico, PartidoEliminatorio, PronosticoEliminatorio, Mensaje, Desafio


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


def ranking(request):
    usuarios = User.objects.filter(is_superuser=False)

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

    tabla = []
    for u in usuarios:
        prons_f1 = Pronostico.objects.filter(usuario=u).select_related('partido')
        pts_f1 = sum(p.puntos() for p in prons_f1)

        prons_f2 = PronosticoEliminatorio.objects.filter(usuario=u).select_related('partido')
        pts_f2 = sum(p.puntos() for p in prons_f2)

        bonus = 0
        if campeon:
            try:
                pron_final = PronosticoEliminatorio.objects.get(
                    usuario=u, partido__ronda='FIN'
                )
                pred_campeon = pron_final.local if (pron_final.goles_l or 0) > (pron_final.goles_v or 0) else pron_final.visita
                if pred_campeon == campeon:
                    bonus += 5
                elif pred_campeon == subcampeon:
                    bonus += 3
            except PronosticoEliminatorio.DoesNotExist:
                pass

        if tercero:
            try:
                pron_3pl = PronosticoEliminatorio.objects.get(
                    usuario=u, partido__ronda='3PL'
                )
                pred_3 = pron_3pl.local if (pron_3pl.goles_l or 0) > (pron_3pl.goles_v or 0) else pron_3pl.visita
                if pred_3 == tercero:
                    bonus += 2
                elif pred_3 == cuarto:
                    bonus += 1
            except PronosticoEliminatorio.DoesNotExist:
                pass

        total = pts_f1 + pts_f2 + bonus
        tabla.append({
            'usuario': u,
            'pts_f1': pts_f1,
            'pts_f2': pts_f2,
            'bonus': bonus,
            'total': total,
        })

    tabla.sort(key=lambda x: x['total'], reverse=True)

    partidos_jugados = Partido.objects.filter(jugado=True).count()
    total_partidos = Partido.objects.count()
    
    # Progreso de pronósticos por usuario (solo para jefe)
    progreso = []
    for u in usuarios:
        total_prons = Pronostico.objects.filter(usuario=u).count()
        progreso.append({
            'usuario': u,
            'completados': total_prons,
            'porcentaje': round((total_prons / 72) * 100),
        })
    progreso.sort(key=lambda x: x['porcentaje'], reverse=True)
    
    
    # Desafíos para el popup
    desafios_activos = Desafio.objects.filter(
        estado='aceptado'
    ).select_related('retador', 'retado', 'partido').order_by('-creado_en')

    desafios_ctx = []
    for d in desafios_activos:
        g = d.ganador()
        desafios_ctx.append({
            'desafio': d,
            'ganador': g,
            'empate': g is None and d.partido.jugado,
            'pendiente': not d.partido.jugado,
        })

    return render(request, 'prode/ranking.html', {
    'tabla': tabla,
    'partidos_jugados': partidos_jugados,
    'total_partidos': total_partidos,
    'progreso': progreso,
    'desafios': desafios_ctx,
    })


def partidos(request):
    partidos = Partido.objects.all()
    return render(request, 'prode/partidos.html', {'partidos': partidos})


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
                    partido.jugado = jugado == 'on'
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
                    partido.jugado = jugado == 'on'
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

    partidos = PartidoEliminatorio.objects.all().order_by('orden')
    partidos_con_equipos = [p for p in partidos if p.local and p.visita]

    if request.method == 'POST':
        for partido in partidos_con_equipos:
            gl = request.POST.get(f'gl_{partido.id}', '').strip()
            gv = request.POST.get(f'gv_{partido.id}', '').strip()

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
        partidos_ctx.append({
            'partido': p,
            'ronda_nombre': rondas.get(p.ronda, p.ronda),
            'gl': pron.goles_l if pron else None,
            'gv': pron.goles_v if pron else None,
            'pts': pron.puntos() if pron else None,
        })

    return render(request, 'prode/pronosticos_eliminatoria.html', {
        'partidos': partidos_ctx,
    })


def eliminatoria(request):
    partidos = PartidoEliminatorio.objects.all().order_by('orden')

    rondas = {
        'R32': 'Round of 32',
        'R16': 'Round of 16',
        'QF':  'Cuartos de final',
        'SF':  'Semifinal',
        '3PL': 'Tercer y cuarto lugar',
        'FIN': 'Final',
    }

    partidos_ctx = []
    for p in partidos:
        partidos_ctx.append({
            'partido': p,
            'ronda_nombre': rondas.get(p.ronda, p.ronda),
            'local': p.local or p.slot_local,
            'visita': p.visita or p.slot_visita,
        })

    return render(request, 'prode/eliminatoria.html', {'partidos': partidos_ctx})


def bracket(request):
    partidos = PartidoEliminatorio.objects.all().order_by('orden')

    def ganador(p):
        if not p.jugado:
            return None
        r = p.resultado_real()
        return p.local if r == 'L' else p.visita

    def fmt(p):
        return {
            'id': p.id,
            'orden': p.orden,
            'local': p.local or p.slot_local,
            'visita': p.visita or p.slot_visita,
            'gl': p.goles_l,
            'gv': p.goles_v,
            'pl': p.penales_l,
            'pv': p.penales_v,
            'jugado': p.jugado,
            'ganador': ganador(p),
        }

    r32 = {p.orden: fmt(p) for p in partidos.filter(ronda='R32')}
    r16 = {p.orden: fmt(p) for p in partidos.filter(ronda='R16')}
    qf  = {p.orden: fmt(p) for p in partidos.filter(ronda='QF')}
    sf  = {p.orden: fmt(p) for p in partidos.filter(ronda='SF')}
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


def reglas(request):
    hoy = date.today()
    cierre = date(2026, 6, 8)
    abierto = hoy <= cierre
    return render(request, 'prode/reglas.html', {'abierto': abierto})



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
            if ronda and (local or slot_local) and (visita or slot_visita):
                ultimo = PartidoEliminatorio.objects.filter(ronda=ronda).count()
                PartidoEliminatorio.objects.create(
                    ronda=ronda,
                    slot_local=slot_local or local,
                    slot_visita=slot_visita or visita,
                    local=local,
                    visita=visita,
                    orden=PartidoEliminatorio.objects.count() + 1,
                )
                messages.success(request, f'Partido agregado al {dict(RONDAS).get(ronda)}.')

        elif accion == 'editar':
            partido_id = request.POST.get('partido_id')
            try:
                partido = PartidoEliminatorio.objects.get(id=partido_id)
                partido.local  = request.POST.get(f'local_{partido_id}', '').strip()
                partido.visita = request.POST.get(f'visita_{partido_id}', '').strip()
                gl = request.POST.get(f'gl_{partido_id}', '').strip()
                gv = request.POST.get(f'gv_{partido_id}', '').strip()
                jugado = request.POST.get(f'jugado_{partido_id}')
                pl = request.POST.get(f'pl_{partido_id}', '').strip()
                pv = request.POST.get(f'pv_{partido_id}', '').strip()
                if gl != '' and gv != '':
                    partido.goles_l = int(gl)
                    partido.goles_v = int(gv)
                    partido.jugado = jugado == 'on'
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
        partidos_por_ronda[nombre] = PartidoEliminatorio.objects.filter(ronda=codigo).order_by('orden')

    return render(request, 'prode/gestionar_eliminatoria.html', {
        'partidos_por_ronda': partidos_por_ronda,
        'rondas': RONDAS,
    })
    
@login_required(login_url='login')
def chat(request):
    from django.utils import timezone

    # Obtener o crear perfil
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        texto = request.POST.get('texto', '').strip()
        if texto and len(texto) <= 300:
            Mensaje.objects.create(usuario=request.user, texto=texto)
        # Actualizar última visita
        perfil.ultima_visita_chat = timezone.now()
        perfil.save()
        return redirect('chat')

    # Actualizar última visita al entrar
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

    return render(request, 'prode/desafios.html', {
        'enviados': enviados,
        'recibidos': recibidos,
        'usuarios': usuarios,
        'partidos': partidos,
    })


@login_required(login_url='login')
def crear_desafio(request):
    if request.method == 'POST':
        retado_id = request.POST.get('retado')
        partido_id = request.POST.get('partido')
        monto = request.POST.get('monto', '0').strip()
        gl = request.POST.get('gl', '').strip()
        gv = request.POST.get('gv', '').strip()

        try:
            retado = User.objects.get(id=retado_id)
            partido = Partido.objects.get(id=partido_id)
            gl_int = int(gl)
            gv_int = int(gv)
            monto_int = int(monto) if monto else 0

            if retado == request.user:
                messages.error(request, 'No puedes desafiarte a ti mismo.')
            elif partido.jugado:
                messages.error(request, 'Ese partido ya se jugó.')
            else:
                Desafio.objects.create(
                    retador=request.user,
                    retado=retado,
                    partido=partido,
                    monto=monto_int,
                    gl_retador=gl_int,
                    gv_retador=gv_int,
                )
                messages.success(request, f'¡Desafío enviado a {retado.username}!')
        except (ValueError, User.DoesNotExist, Partido.DoesNotExist):
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
    ).select_related('retador', 'retado', 'partido').order_by('-creado_en')

    historial = []
    for d in desafios:
        g = d.ganador()
        historial.append({
            'desafio': d,
            'ganador': g,
            'empate': g is None and d.partido.jugado,
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