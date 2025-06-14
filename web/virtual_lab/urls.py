from django.urls import path

from .views import (
    physics_electrical_circuit_view,
    physics_inclined_view,
    physics_mass_spring_view,
    physics_pendulum_view,
    physics_projectile_view,
    virtual_lab_home,
)

app_name = "virtual_lab"

urlpatterns = [
    path("", virtual_lab_home, name="virtual_lab_home"),
    path("physics/pendulum/", physics_pendulum_view, name="physics_pendulum"),
    path("physics/projectile/", physics_projectile_view, name="physics_projectile"),
    path("physics/inclined/", physics_inclined_view, name="physics_inclined"),
    path("physics/mass_spring/", physics_mass_spring_view, name="physics_mass_spring"),
    path("physics/circuit/", physics_electrical_circuit_view, name="physics_electrical_circuit"),
]
