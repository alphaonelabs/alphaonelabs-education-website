# web/virtual_lab/views.py

from django.shortcuts import render


def virtual_lab_home(request):
    """
    Renders the Virtual Lab home page (home.html).
    """
    return render(request, "virtual_lab/home.html")


def physics_pendulum_view(request):
    """
    Renders the Pendulum Motion simulation page (physics/pendulum.html).
    """
    return render(request, "virtual_lab/physics/pendulum.html")


def physics_projectile_view(request):
    """
    Renders the Projectile Motion simulation page (physics/projectile.html).
    """
    return render(request, "virtual_lab/physics/projectile.html")


def physics_inclined_view(request):
    """
    Renders the Inclined Plane simulation page (physics/inclined.html).
    """
    return render(request, "virtual_lab/physics/inclined.html")


def physics_mass_spring_view(request):
    return render(request, "virtual_lab/physics/mass_spring.html")


def physics_electrical_circuit_view(request):
    return render(request, "virtual_lab/physics/circuit.html")
