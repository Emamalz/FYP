from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

from . import views
from .views import home, fraud_view

urlpatterns = [
    # Home
    path("", home, name="home"),

    # Auth
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # Main pages
    path("mumu/", views.mumu, name="mumu"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("transactions/", views.transactions, name="transactions"),
    path("fraud/", fraud_view, name="fraud"),
    path("orders/", views.orders, name="orders"),
    path("chargebacks/", views.chargebacks, name="chargebacks"),
    path("models/", views.models, name="models"),

    # Account
    path("account/", views.account_settings, name="account"),

    # Password change (logged in)
    path(
        "password-change/",
        views.CustomPasswordChangeView.as_view(),
        name="password_change"
    ),

    # Password reset (logged out)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="dashboard/password_reset.html"
        ),
        name="password_reset"
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="dashboard/password_reset_done.html"
        ),
        name="password_reset_done"
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="dashboard/password_reset_confirm.html"
        ),
        name="password_reset_confirm"
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="dashboard/password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),

    # Password reset while logged in
    path(
        "password-reset/logged-in/",
        auth_views.PasswordResetView.as_view(
            template_name="dashboard/password_reset_loggedin.html"
        ),
        name="password_reset_loggedin"
    ),
]
