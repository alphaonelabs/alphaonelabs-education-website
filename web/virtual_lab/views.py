# web/virtual_lab/views.py

import json

import requests
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


# Piston’s public execute endpoint (rate-limited to 5 req/s) :contentReference[oaicite:0]{index=0}
PISTON_EXECUTE_URL = "https://emkc.org/api/v2/piston/execute"

LANG_FILE_EXT = {
    "python": "py",
    "javascript": "js",
    "c": "c",
    "cpp": "cpp",
}


def code_editor_view(request):
    return render(request, "virtual_lab/code_editor/code_editor.html")


@require_POST
def evaluate_code(request):
    """
    Proxy code + stdin to Piston and return its JSON result.
    """
    data = json.loads(request.body)
    source_code = data.get("code", "")
    language = data.get("language", "python")  # e.g. "python","javascript","c","cpp"
    stdin_text = data.get("stdin", "")

    # Package content for Piston
    ext = LANG_FILE_EXT.get(language, "txt")
    files = [{"name": f"main.{ext}", "content": source_code}]
    payload = {
        "language": language,
        "version": "*",  # semver selector; '*' picks latest :contentReference[oaicite:1]{index=1}
        "files": files,
        "stdin": stdin_text,
        "args": [],
    }

    try:
        resp = requests.post(PISTON_EXECUTE_URL, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        return JsonResponse({"stderr": str(e)}, status=502)

    result = resp.json()
    # Piston returns a structure like:
    # { language, version, run: { stdout, stderr, code, signal, output } }
    run = result.get("run", {})
    return JsonResponse(
        {
            "stdout": run.get("stdout", run.get("output", "")),
            "stderr": run.get("stderr", ""),
        }
    )
