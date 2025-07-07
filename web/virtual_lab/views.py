# web/virtual_lab/views.py

import json
import os
import subprocess
import sys
import tempfile

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST


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


def code_editor_view(request):
    # note the extra “code_editor/” directory in the path
    return render(request, "virtual_lab/code_editor/code_editor.html")


@require_POST
def evaluate_code(request):
    """
    Runs Python code locally in a temp file.
    """
    data = json.loads(request.body)
    code = data.get("code", "")
    stdin = data.get("stdin", "")

    # write to a temp file
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name

    try:
        proc = subprocess.run([sys.executable, path], input=stdin, capture_output=True, text=True, timeout=5)
        return JsonResponse({"stdout": proc.stdout, "stderr": proc.stderr})
    except subprocess.TimeoutExpired:
        return JsonResponse({"stdout": "", "stderr": "Execution timed out."}, status=504)
    finally:
        os.remove(path)
