from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Partido, Pronostico


def login_view(request):
    if request.user.is_authenticated:
        return redirect('ranking')
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        print(f'DEBUG login: usuario={username} password={password}')
        user = authenticate(request, username=username, password=password)
        print(f'DEBUG authenticate resultado: {user}')
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
    partidos = Partido.objects.all()

    if request.method == 'POST':
        for partido in partidos:
            gl = request.POST.get(f'gl_{partido.id}', '').strip()
            gv = request.POST.get(f'gv_{partido.id}', '').strip()
            if gl != '' and gv != '':
                try:
                    gl_int = int(gl)
                    gv_int = int(gv)
                    if gl_int < 0 or gv_int < 0:
                        continue
                    Pronostico.objects.update_or_create(
                        usuario=request.user,
                        partido=partido,
                        defaults={'goles_l': gl_int, 'goles_v': gv_int}
                    )
                except ValueError:
                    pass
        messages.success(request, '¡Pronósticos guardados!')
        return redirect('pronosticos')

    # Armar dict con pronósticos existentes
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
            'pts': pron.puntos() if pron else None,
        })

    return render(request, 'prode/pronosticos.html', {'partidos': partidos_ctx})






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
        messages.success(request, 'Resultados guardados.')
        return redirect('cargar_resultados')

    return render(request, 'prode/cargar_resultados.html', {'partidos': partidos})