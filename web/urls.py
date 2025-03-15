from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path

from . import admin_views, views
from .views import GoodsListingView, add_goods_to_cart, sales_analytics, sales_data

# Non-prefixed URLs
urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),  # Language selection URLs
    path("captcha/", include("captcha.urls")),  # CAPTCHA URLs should not be language-prefixed
]

if settings.DEBUG:
    urlpatterns.append(path("__reload__/", include("django_browser_reload.urls")))  # Browser reload URLs

# Language-prefixed URLs
urlpatterns += i18n_patterns(
    path("", views.index, name="index"),
    path("learn/", views.learn, name="learn"),
    path("teach/", views.teach, name="teach"),
    path("about/", views.about, name="about"),
    path("blog/", views.blog_list, name="blog_list"),
    path("blog/create/", views.create_blog_post, name="create_blog_post"),
    path("blog/tag/<str:tag>/", views.blog_tag, name="blog_tag"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),
    # Authentication URLs
    path("accounts/signup/", views.signup_view, name="account_signup"),  # Our custom signup view
    path("accounts/", include("allauth.urls")),
    path("profile/", views.profile, name="profile"),
    path("accounts/profile/", views.profile, name="accounts_profile"),
    # Dashboard URLs
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),
    path("dashboard/teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path("dashboard/content/", views.content_dashboard, name="content_dashboard"),
    # Course Management
    path("courses/create/", views.create_course, name="create_course"),
    path("courses/search/", views.course_search, name="course_search"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
    path("courses/<slug:course_slug>/enroll/", views.enroll_course, name="enroll_course"),
    path("courses/<slug:slug>/add-session/", views.add_session, name="add_session"),
    path("courses/<slug:slug>/edit/", views.update_course, name="update_course"),
    path("sessions/<int:session_id>/edit/", views.edit_session, name="edit_session"),
    path("courses/<slug:slug>/add-review/", views.add_review, name="add_review"),
    path("courses/<slug:slug>/delete/", views.delete_course, name="delete_course"),
    path("courses/<slug:slug>/add-session/", views.add_session, name="add_session"),
    path("courses/<slug:slug>/confirm-rolled-sessions/", views.confirm_rolled_sessions, name="confirm_rolled_sessions"),
    path("courses/<slug:slug>/message-students/", views.message_enrolled_students, name="message_students"),
    path("teachers/<int:teacher_id>/message/", views.message_teacher, name="message_teacher"),
    # Payment URLs
    path(
        "courses/<slug:slug>/create-payment-intent/",
        views.create_payment_intent,
        name="create_payment_intent",
    ),
    path("stripe-webhook/", views.stripe_webhook, name="stripe_webhook"),
    # Admin and Utilities
    path("github_update/", views.github_update, name="github_update"),
    path(f"{settings.ADMIN_URL}/dashboard/", admin_views.admin_dashboard, name="admin_dashboard"),
    path(f"{settings.ADMIN_URL}/", admin.site.urls),
    path("subjects/", views.subjects, name="subjects"),
    # Progress tracking URLs
    path(
        "sessions/<int:session_id>/attendance/",
        views.mark_session_attendance,
        name="mark_session_attendance",
    ),
    path(
        "sessions/<int:session_id>/complete/",
        views.mark_session_completed,
        name="mark_session_completed",
    ),
    path(
        "enrollment/<int:enrollment_id>/progress/",
        views.student_progress,
        name="student_progress",
    ),
    path(
        "courses/<slug:slug>/progress/",
        views.course_progress_overview,
        name="course_progress_overview",
    ),
    path(
        "courses/<slug:slug>/materials/upload/",
        views.upload_material,
        name="upload_material",
    ),
    path(
        "courses/<slug:slug>/materials/<int:material_id>/delete/",
        views.delete_material,
        name="delete_material",
    ),
    path(
        "courses/<slug:slug>/materials/<int:material_id>/download/",
        views.download_material,
        name="download_material",
    ),
    path(
        "courses/<slug:slug>/marketing/",
        views.course_marketing,
        name="course_marketing",
    ),
    path(
        "courses/<slug:slug>/analytics/",
        views.course_analytics,
        name="course_analytics",
    ),
    path("calendar/feed/", views.calendar_feed, name="calendar_feed"),
    path(
        "calendar/session/<int:session_id>/",
        views.calendar_links,
        name="calendar_links",
    ),
    # Forum URLs
    path("forum/", views.forum_categories, name="forum_categories"),
    path("forum/category/create/", views.create_forum_category, name="create_forum_category"),
    path("forum/category/<slug:slug>/", views.forum_category, name="forum_category"),
    path("forum/category/<slug:category_slug>/create/", views.create_topic, name="create_topic"),
    path(
        "forum/<slug:category_slug>/<int:topic_id>/",
        views.forum_topic,
        name="forum_topic",
    ),
    path("forum/topic/<int:topic_id>/edit/", views.edit_topic, name="edit_topic"),
    # Peer Networking URLs
    path("peers/", views.peer_connections, name="peer_connections"),
    path(
        "peers/connect/<int:user_id>/",
        views.send_connection_request,
        name="send_connection_request",
    ),
    path(
        "peers/handle/<int:connection_id>/<str:action>/",
        views.handle_connection_request,
        name="handle_connection_request",
    ),
    path("peers/messages/<int:user_id>/", views.peer_messages, name="peer_messages"),
    # Study Groups URLs
    path("courses/<int:course_id>/groups/", views.study_groups, name="study_groups"),
    path("groups/<int:group_id>/", views.study_group_detail, name="study_group_detail"),
    path("sessions/<int:session_id>/", views.session_detail, name="session_detail"),
    path("sitemap/", views.sitemap, name="sitemap"),
    # Cart URLs
    path("cart/", views.cart_view, name="cart_view"),
    path("cart/add/course/<int:course_id>/", views.add_course_to_cart, name="add_course_to_cart"),
    path("cart/add/session/<int:session_id>/", views.add_session_to_cart, name="add_session_to_cart"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/payment-intent/", views.create_cart_payment_intent, name="create_cart_payment_intent"),
    path("cart/checkout/success/", views.checkout_success, name="checkout_success"),
    path("markdownx/", include("markdownx.urls")),
    # Course Invitation URLs
    path("courses/<int:course_id>/invite/", views.invite_student, name="invite_student"),
    path("terms/", views.terms, name="terms"),
    path("feedback/", views.feedback, name="feedback"),
    path("stripe/connect/onboarding/", views.stripe_connect_onboarding, name="stripe_connect_onboarding"),
    path("stripe/connect/webhook/", views.stripe_connect_webhook, name="stripe_connect_webhook"),
    path("courses/<slug:slug>/calendar/", views.get_course_calendar, name="course_calendar"),
    # Calendar URLs
    path("calendar/create/", views.create_calendar, name="create_calendar"),
    path("calendar/<str:share_token>/", views.view_calendar, name="view_calendar"),
    path("calendar/<str:share_token>/add-slot", views.add_time_slot, name="add_time_slot"),
    path("calendar/<str:share_token>/remove-slot", views.remove_time_slot, name="remove_time_slot"),
    path("calendar/<str:share_token>/data", views.get_calendar_data, name="get_calendar_data"),
    path("status/", views.system_status, name="system_status"),
    # Challenge URLs
    path("challenges/<int:week_number>/", views.challenge_detail, name="challenge_detail"),
    path("challenges/<int:week_number>/submit/", views.challenge_submit, name="challenge_submit"),
    path("current-weekly-challenge/", views.current_weekly_challenge, name="current_weekly_challenge"),
    path("fetch-video-title/", views.fetch_video_title, name="fetch_video_title"),
    # Quiz URLS
    path("quiz/<int:quiz_id>",views.current_live_quiz,name="current_live_quiz"),
    path("quiz/<int:quiz_id>/submit",views.submit_quiz,name="submit_quiz"),
    path("quiz/<int:quiz_id>/leaderboard",views.leaderboard,name="leaderboard"),
    # Storefront Management
    path("store/create/", login_required(views.StorefrontCreateView.as_view()), name="storefront_create"),
    path(
        "store/<slug:store_slug>/edit/",
        login_required(views.StorefrontUpdateView.as_view()),
        name="storefront_update",
    ),
    path("storefront/<slug:store_slug>/", views.StorefrontDetailView.as_view(), name="storefront_detail"),
    # Product (Goods) Management
    path("goods/", views.GoodsListView.as_view(), name="goods_list"),
    path("goods/<int:pk>/", views.GoodsDetailView.as_view(), name="goods_detail"),
    path("store/<slug:store_slug>/goods/create/", login_required(views.GoodsCreateView.as_view()), name="goods_create"),
    path("goods/<int:pk>/edit/", views.GoodsUpdateView.as_view(), name="goods_update"),
    path("goods/delete/<int:pk>/", views.GoodsDeleteView.as_view(), name="goods_delete"),
    path("goods/add-to-cart/<int:pk>/", add_goods_to_cart, name="add_goods_to_cart"),
    path("products/", GoodsListingView.as_view(), name="goods_listing"),
    # Order Management
    path("orders/<int:pk>/", login_required(views.OrderDetailView.as_view()), name="order_detail"),
    path(
        "store/<slug:store_slug>/orders/",
        login_required(views.OrderManagementView.as_view()),
        name="store_order_management",
    ),
    path("orders/item/<int:item_id>/update-status/", views.update_order_status, name="update_order_status"),
    # Analytics
    path(
        "store/<slug:store_slug>/analytics/",
        login_required(views.StoreAnalyticsView.as_view()),
        name="store_analytics",
    ),
    path(
        "admin/merchandise-analytics/",
        login_required(views.AdminMerchAnalyticsView.as_view()),
        name="admin_merch_analytics",
    ),
    path("analytics/", sales_analytics, name="sales_analytics"),
    path("analytics/data/", sales_data, name="sales_data"),
    prefix_default_language=True,
)

handler404 = "web.views.custom_404"
handler500 = "web.views.custom_500"
handler429 = "web.views.custom_429"
