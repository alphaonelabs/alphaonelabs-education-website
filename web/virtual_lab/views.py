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
    """
    Renders the Mass-Spring Oscillation simulation page (physics/mass_spring.html).
    """
    return render(request, "virtual_lab/physics/mass_spring.html")


def physics_electrical_circuit_view(request):
    """
    Renders the Electrical Circuit simulation page (physics/circuit.html).
    """
    return render(request, "virtual_lab/physics/circuit.html")


def chemistry_home(request):
    return render(request, "virtual_lab/chemistry/index.html")


def titration_view(request):
    return render(request, "virtual_lab/chemistry/titration.html")


def reaction_rate_view(request):
    return render(request, "virtual_lab/chemistry/reaction_rate.html")


def solubility_view(request):
    return render(request, "virtual_lab/chemistry/solubility.html")


def precipitation_view(request):
    return render(request, "virtual_lab/chemistry/precipitation.html")


def ph_indicator_view(request):
    return render(request, "virtual_lab/chemistry/ph_indicator.html")
