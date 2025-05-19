import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import teacher_required
from .forms import VirtualClassroomForm, VirtualClassroomCustomizationForm
from .models import VirtualClassroom, VirtualClassroomCustomization

@login_required
def virtual_classroom_list(request):
    """View for listing all virtual classrooms."""
    classrooms = VirtualClassroom.objects.filter(is_active=True)
    if not request.user.profile.is_teacher:
        # Students can only see classrooms they are enrolled in
        classrooms = classrooms.filter(course__enrollments__student=request.user)
    return render(request, "virtual_classroom/list.html", {"classrooms": classrooms})

@login_required
@teacher_required
def virtual_classroom_create(request):
    """View for creating a new virtual classroom."""
    if request.method == "POST":
        form = VirtualClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.teacher = request.user
            classroom.save()
            messages.success(request, "Virtual classroom created successfully!")
            return redirect("virtual_classroom_detail", classroom_id=classroom.id)
    else:
        form = VirtualClassroomForm()
    return render(request, "virtual_classroom/create.html", {"form": form})

@login_required
def virtual_classroom_detail(request, classroom_id):
    """View for displaying a virtual classroom."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id)
    
    # Check if user has access
    if not request.user.profile.is_teacher and not classroom.course.enrollments.filter(student=request.user).exists():
        messages.error(request, "You don't have access to this classroom.")
        return redirect("virtual_classroom_list")
    
    # Get or create customization
    customization = classroom.customization_settings if hasattr(classroom, 'customization_settings') else None
    
    if request.method == "POST" and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Handle AJAX request to save customization
        data = json.loads(request.body)
        if not customization:
            customization = VirtualClassroomCustomization.objects.create(
                classroom=classroom,
                wall_color=data.get('wallColor', '#FFFFFF'),
                floor_color=data.get('floorColor', '#F5F5F5'),
                desk_color=data.get('deskColor', '#8B4513'),
                chair_color=data.get('chairColor', '#4B0082'),
                board_color=data.get('boardColor', '#000000'),
                number_of_rows=data.get('numRows', 5),
                desks_per_row=data.get('desksPerRow', 6),
                has_plants=data.get('hasPlants', True),
                has_windows=data.get('hasWindows', True),
                has_bookshelf=data.get('hasBookshelf', True),
                has_clock=data.get('hasClock', True),
                has_carpet=data.get('hasCarpet', True)
            )
        else:
            customization.wall_color = data.get('wallColor', customization.wall_color)
            customization.floor_color = data.get('floorColor', customization.floor_color)
            customization.desk_color = data.get('deskColor', customization.desk_color)
            customization.chair_color = data.get('chairColor', customization.chair_color)
            customization.board_color = data.get('boardColor', customization.board_color)
            customization.number_of_rows = data.get('numRows', customization.number_of_rows)
            customization.desks_per_row = data.get('desksPerRow', customization.desks_per_row)
            customization.has_plants = data.get('hasPlants', customization.has_plants)
            customization.has_windows = data.get('hasWindows', customization.has_windows)
            customization.has_bookshelf = data.get('hasBookshelf', customization.has_bookshelf)
            customization.has_clock = data.get('hasClock', customization.has_clock)
            customization.has_carpet = data.get('hasCarpet', customization.has_carpet)
            customization.save()
        
        return JsonResponse({"status": "success"})
    
    context = {
        "classroom": classroom,
        "customization": customization
    }
    return render(request, "virtual_classroom/index.html", context)

@login_required
@teacher_required
def virtual_classroom_edit(request, classroom_id):
    """View for editing a virtual classroom."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id, teacher=request.user)
    if request.method == "POST":
        form = VirtualClassroomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, "Virtual classroom updated successfully!")
            return redirect("virtual_classroom_detail", classroom_id=classroom.id)
    else:
        form = VirtualClassroomForm(instance=classroom)
    return render(request, "virtual_classroom/edit.html", {"form": form, "classroom": classroom})

@login_required
@teacher_required
def virtual_classroom_delete(request, classroom_id):
    """View for deleting a virtual classroom."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id, teacher=request.user)
    if request.method == "POST":
        classroom.is_active = False
        classroom.save()
        messages.success(request, "Virtual classroom deleted successfully!")
        return redirect("virtual_classroom_list")
    return render(request, "virtual_classroom/delete.html", {"classroom": classroom})

@login_required
@teacher_required
def virtual_classroom_customize(request, classroom_id):
    """View for customizing a virtual classroom."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id, teacher=request.user)
    customization = classroom.customization_settings if hasattr(classroom, 'customization_settings') else None
    
    if request.method == "POST":
        form = VirtualClassroomCustomizationForm(request.POST, instance=customization)
        if form.is_valid():
            customization = form.save(commit=False)
            customization.classroom = classroom
            customization.save()
            messages.success(request, "Classroom customization saved successfully!")
            return redirect("virtual_classroom_detail", classroom_id=classroom.id)
    else:
        form = VirtualClassroomCustomizationForm(instance=customization)
    
    return render(request, "virtual_classroom/customize.html", {
        "form": form,
        "classroom": classroom,
        "customization": customization
    }) 