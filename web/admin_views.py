from datetime import timedelta

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from .models import Order


@staff_member_required
def admin_dashboard(request):
    """Admin dashboard showing model statistics."""
    # Add admin site context
    context = dict(
        admin.site.each_context(request),
        title="Dashboard",
    )

    # Get the date range for historical data (last 30 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)

    # Function to get historical data for a model
    def get_model_history(model):
        date_field = next(
            (f.name for f in model._meta.fields if f.name in ["created_at", "date_joined"]),
            None,
        )
        if not date_field:
            return []

        filter_kwargs = {f"{date_field}__range": (start_date, end_date)}
        return (
            model.objects.filter(**filter_kwargs)
            .annotate(date=TruncDate(date_field))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

    # Get all registered models
    models_to_track = []
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            # Skip models without creation date fields
            if any(f.name in ["created_at", "date_joined"] for f in model._meta.fields):
                # Get admin URL if model is registered in admin
                admin_url = None
                if admin.site.is_registered(model):
                    admin_url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")

                models_to_track.append(
                    {"model": model, "title": model._meta.verbose_name_plural.title(), "admin_url": admin_url}
                )

    stats = []
    for model_info in models_to_track:
        model = model_info["model"]
        current_count = model.objects.count()

        # Get historical data
        history_data = get_model_history(model)
        history_list = [0] * 30  # Initialize with zeros

        # Fill in actual counts
        for entry in history_data:
            days_ago = (end_date.date() - entry["date"]).days
            if 0 <= days_ago < 30:
                history_list[days_ago] = entry["count"]

        stats.append(
            {
                "title": model_info["title"],
                "count": current_count,
                "history": list(reversed(history_list)),  # Reverse to show oldest to newest
                "admin_url": model_info["admin_url"],
            }
        )

    # Sort stats by total count descending
    stats.sort(key=lambda x: x["count"], reverse=True)

    # Merchandise sales analytics
    merchandise_sales = (
        Order.objects.filter(status="completed", created_at__date__gte=start_date.date())
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total_sales=Sum("total_price"))
        .order_by("date")
    )

    # Initialize sales data with 0 for the last 30 days
    merchandise_sales_data = {start_date.date() + timedelta(days=i): 0 for i in range(30)}

    for entry in merchandise_sales:
        if entry["date"] in merchandise_sales_data:
            merchandise_sales_data[entry["date"]] = entry["total_sales"]

    context["merchandise_sales"] = list(merchandise_sales_data.values())
    context["stats"] = stats

    return render(request, "admin/dashboard.html", context)
