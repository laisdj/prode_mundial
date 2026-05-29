from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Partido, Pronostico
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
    from collections import defaultdict

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

    # Calcular pts y dg, ordenar
    grupos_ordenados = {}
    for letra, equipos in grupos.items():
        tabla = []
        for nombre, stats in equipos.items():
            stats['pts'] = stats['g'] * 3 + stats['e']
            stats['dg'] = stats['gf'] - stats['gc']
            stats['nombre'] = nombre
            tabla.append(stats)
        tabla.sort(key=lambda x: (-x['pts'], -x['dg'], -x['gf']))
        grupos_ordenados[letra] = tabla

    return render(request, 'prode/clasificacion.html', {'grupos': grupos_ordenados})