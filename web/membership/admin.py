from django.contrib import admin
from django.utils.html import format_html

from .models import MembershipPlan, MembershipSubscriptionEvent, UserMembership


@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "display_price",
        "display_billing_period",
        "is_popular",
        "is_active",
        "order",
        "created_at",
    )
    list_filter = ("is_active", "is_popular", "billing_period")
    search_fields = ("name", "description")
    ordering = ("order", "price_monthly")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Plan Information", {"fields": ("name", "description", "is_active", "is_popular", "order")}),
        (
            "Pricing",
            {
                "fields": (
                    "billing_period",
                    "price_monthly",
                    "price_yearly",
                ),
            },
        ),
        (
            "Stripe Integration",
            {
                "fields": ("stripe_monthly_price_id", "stripe_yearly_price_id"),
            },
        ),
        (
            "Features",
            {
                "fields": ("features",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def display_billing_period(self, obj):
        return obj.get_billing_period_display()

    display_billing_period.short_description = "Billing Period"

    def display_price(self, obj):
        if obj.billing_period == "monthly":
            return f"${obj.price_monthly}/month"
        elif obj.billing_period == "yearly":
            return f"${obj.price_yearly}/year"
        else:
            return f"${obj.price_monthly}/month, ${obj.price_yearly}/year"

    display_price.short_description = "Price"


class MembershipPlanInline(admin.TabularInline):
    model = MembershipPlan
    extra = 0
    show_change_link = True
    fields = ("name", "display_price", "display_billing_period", "is_active")
    readonly_fields = ("name", "display_price", "display_billing_period", "is_active")
    can_delete = False

    def display_billing_period(self, obj):
        return obj.get_billing_period_display()

    display_billing_period.short_description = "Billing Period"

    def display_price(self, obj):
        if obj.billing_period == "monthly":
            return f"${obj.price_monthly}/month"
        elif obj.billing_period == "yearly":
            return f"${obj.price_yearly}/year"
        else:
            return f"${obj.price_monthly}/month, ${obj.price_yearly}/year"

    display_price.short_description = "Price"

    def has_add_permission(self, request, obj=None):
        return False


class MembershipSubscriptionEventInline(admin.TabularInline):
    model = MembershipSubscriptionEvent
    extra = 0
    max_num = 10
    readonly_fields = ("event_type", "created_at", "stripe_event_id")
    fields = ("event_type", "created_at", "stripe_event_id")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(UserMembership)
class UserMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan",
        "status_colored",
        "display_active",
        "start_date",
        "end_date",
        "cancel_at_period_end",
    )
    list_filter = ("status", "cancel_at_period_end")
    search_fields = ("user__username", "user__email", "stripe_customer_id", "stripe_subscription_id")
    readonly_fields = ("created_at", "updated_at", "days_until_expiration_display")
    raw_id_fields = ("user", "plan")

    inlines = [MembershipSubscriptionEventInline]

    fieldsets = (
        (
            "User Information",
            {
                "fields": (
                    "user",
                    "plan",
                )
            },
        ),
        (
            "Membership Status",
            {
                "fields": (
                    "status",
                    "start_date",
                    "end_date",
                    "cancel_at_period_end",
                    "days_until_expiration_display",
                ),
            },
        ),
        (
            "Stripe Information",
            {
                "fields": ("stripe_customer_id", "stripe_subscription_id"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def status_colored(self, obj):
        colors = {
            "active": "green",
            "trialing": "blue",
            "past_due": "orange",
            "canceled": "red",
            "incomplete": "orange",
            "incomplete_expired": "red",
            "unpaid": "red",
            "inactive": "gray",
        }
        color = colors.get(obj.status, "gray")
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())

    status_colored.short_description = "Status"

    def display_active(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')

    display_active.short_description = "Active"

    def days_until_expiration_display(self, obj):
        days = obj.days_until_expiration

        if days is None:
            return "Not set"

        if days <= 0:
            return format_html('<span style="color: red;">Expired</span>')
        elif days <= 7:
            return format_html('<span style="color: orange;">{} days</span>', days)
        else:
            return format_html('<span style="color: green;">{} days</span>', days)

    days_until_expiration_display.short_description = "Days Until Expiration"


@admin.register(MembershipSubscriptionEvent)
class MembershipSubscriptionEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "created_at", "stripe_event_id")
    list_filter = ("event_type", "created_at")
    search_fields = ("user__username", "user__email", "stripe_event_id")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user", "membership")

    fieldsets = (
        ("Event Information", {"fields": ("event_type", "user", "membership", "created_at")}),
        (
            "Stripe Information",
            {
                "fields": ("stripe_event_id",),
            },
        ),
        (
            "Event Data",
            {
                "fields": ("data",),
            },
        ),
    )
