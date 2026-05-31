from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import Partido, Pronostico, PartidoEliminatorio, PronosticoEliminatorio
from datetime import date


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
    return render(request, 'prode/ranking.html', {'tabla': tabla})


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

    return render(request, 'prode/mi_clasificacion.html', {'grupos': grupos_ordenados})


@login_required(login_url='login')
def pronosticos(request):
    if request.user.is_staff:
        return redirect('ranking')

    hoy = date.today()
    cierre = date(2026, 6, 4)
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
            if local:
                partido.local = local
            if visita:
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
    cierre = date(2026, 6, 4)
    abierto = hoy <= cierre
    return render(request, 'prode/reglas.html', {'abierto': abierto})