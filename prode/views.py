from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Partido, Pronostico
from datetime import date
from .models import Partido, Pronostico, PartidoEliminatorio, PronosticoEliminatorio


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
    tabla = []
    for u in usuarios:
        prons = Pronostico.objects.filter(usuario=u).select_related('partido')
        pts = sum(p.puntos() for p in prons)
        exactos = sum(1 for p in prons if p.puntos() == 3)
        resultados = sum(1 for p in prons if p.puntos() == 1)
        tabla.append({
            'usuario': u,
            'pts': pts,
            'exactos': exactos,
            'resultados': resultados,
        })
    tabla.sort(key=lambda x: x['pts'], reverse=True)
    return render(request, 'prode/ranking.html', {'tabla': tabla})


def partidos(request):
    partidos = Partido.objects.all()
    return render(request, 'prode/partidos.html', {'partidos': partidos})


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
                # Solo uno está vacío, ignorar
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
            'gl': pron.goles_l if pron else '',
            'gv': pron.goles_v if pron else '',
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
                    gl_int = int(gl)
                    gv_int = int(gv)
                    partido.goles_l = gl_int
                    partido.goles_v = gv_int
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


def reglas(request):
    hoy = date.today()
    cierre = date(2026, 6, 4)
    abierto = hoy <= cierre
    return render(request, 'prode/reglas.html', {'abierto': abierto})

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

    # Agregar equipos sin partidos jugados aún
    todos = Partido.objects.all()
    for p in todos:
        for equipo in [p.local, p.visita]:
            if equipo not in grupos[p.grupo]:
                grupos[p.grupo][equipo] = {'pj':0,'g':0,'e':0,'p':0,'gf':0,'gc':0}

    # Calcular pts y dg, ordenar cada grupo
    grupos_ordenados = {}
    terceros = []  # para calcular mejores 8 terceros

    for letra, equipos in grupos.items():
        tabla = []
        for nombre, stats in equipos.items():
            stats['pts'] = stats['g'] * 3 + stats['e']
            stats['dg'] = stats['gf'] - stats['gc']
            stats['nombre'] = nombre
            stats['estado'] = ''  # se llena después
            tabla.append(stats)
        tabla.sort(key=lambda x: (-x['pts'], -x['dg'], -x['gf']))
        grupos_ordenados[letra] = tabla

        # Guardar el tercero de este grupo para comparar
        if len(tabla) >= 3:
            t = tabla[2].copy()
            t['grupo'] = letra
            terceros.append(t)

    # Ordenar terceros y marcar los 8 mejores
    terceros.sort(key=lambda x: (-x['pts'], -x['dg'], -x['gf']))
    mejores_terceros = set(t['nombre'] for t in terceros[:8])

    # Asignar estado a cada equipo
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

    # Usar pronósticos del usuario en vez de resultados reales
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

    # Agregar equipos sin pronósticos aún
    todos = Partido.objects.all()
    for p in todos:
        for equipo in [p.local, p.visita]:
            if equipo not in grupos[p.grupo]:
                grupos[p.grupo][equipo] = {'pj':0,'g':0,'e':0,'p':0,'gf':0,'gc':0}

    # Calcular pts, dg, ordenar y asignar estado
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