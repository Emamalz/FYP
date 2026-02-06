import os
import json
import pandas as pd

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Sum

from dashboard.models import Transaction


# ===========================
# TRANSACTIONS (CSV-BASED UI)
# ===========================
@login_required
def transactions(request):
    csv_path = os.path.join(
        settings.BASE_DIR,
        "dashboard",
        "data",
        "transactions_ui.csv"
    )

    df = pd.read_csv(csv_path)

    df["transaction_timestamp"] = pd.to_datetime(
        df["transaction_timestamp"],
        dayfirst=True,
        errors="coerce"
    )

    if "unix_time" in df.columns:
        missing = df["transaction_timestamp"].isna()
        df.loc[missing, "transaction_timestamp"] = pd.to_datetime(
            df.loc[missing, "unix_time"],
            unit="s",
            errors="coerce"
        )

    df = df.dropna(subset=["transaction_timestamp"])
    df["transaction_timestamp"] = df["transaction_timestamp"].dt.floor("s")

    df["transaction_amount"] = pd.to_numeric(
        df["transaction_amount"], errors="coerce"
    ) / 100

    df["fraud_label"] = df["fraud_label"].apply(
        lambda x: str(x).strip().lower() == "true"
    )

    start_date = request.GET.get("from")
    end_date = request.GET.get("to")

    if start_date:
        df = df[df["transaction_timestamp"] >= pd.to_datetime(start_date)]

    if end_date:
        df = df[df["transaction_timestamp"] < pd.to_datetime(end_date) + pd.Timedelta(days=1)]

    fraud_only = request.GET.get("fraud") == "1"
    if fraud_only:
        df = df[df["fraud_label"]]

    df = df.sort_values("transaction_timestamp", ascending=False)

    page_size = 50
    page = max(int(request.GET.get("page", 1)), 1)

    total_pages = max((len(df) - 1) // page_size + 1, 1)
    page = min(page, total_pages)

    page_df = df.iloc[(page - 1) * page_size : page * page_size]

    grouped = (
        df.set_index("transaction_timestamp")
          .resample("D")
          .agg(
              total=("transaction_id", "count"),
              fraud=("fraud_label", "sum")
          )
    )

    grouped = grouped[grouped["total"] > 0]

    context = {
        "transactions": page_df.to_dict("records"),
        "page": page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "chart_labels": json.dumps(grouped.index.strftime("%Y-%m-%d").tolist()),
        "total_tx_data": json.dumps(grouped["total"].tolist()),
        "fraud_tx_data": json.dumps(grouped["fraud"].tolist()),
        "from_date": start_date or "",
        "to_date": end_date or "",
        "fraud_only": fraud_only,
    }

    return render(request, "dashboard/transactions.html", context)


# ===========================
# DASHBOARD
# ===========================
@login_required
def dashboard(request):
    return render(request, "dashboard/index.html", {
        "total_transactions": Transaction.objects.count(),
        "fraud_count": Transaction.objects.filter(fraud_label=True).count(),
        "total_volume": round(
            Transaction.objects.aggregate(total=Sum("transaction_amount"))["total"] or 0,
            2
        ),
    })


def home(request):
    return render(request, "dashboard/home.html")


@login_required
def fraud_view(request):
    return render(request, "dashboard/fraud.html")


@login_required
def chargebacks(request):
    return render(request, "dashboard/chargebacks.html")


@login_required
def models(request):
    return render(request, "dashboard/models.html")


def mumu(request):
    return render(request, "dashboard/mumu.html")


@login_required
def account_settings(request):
    if request.method == "POST":
        request.user.email = request.POST.get("email")
        request.user.save()
        messages.success(request, "Account updated successfully.")
    return render(request, "dashboard/account.html")


def signup(request):
    form = UserCreationForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("login")
    return render(request, "dashboard/signup.html", {"form": form})


class UserLoginView(LoginView):
    template_name = "dashboard/login.html"


class CustomPasswordChangeView(PasswordChangeView):
    template_name = "dashboard/password_change.html"
    success_url = reverse_lazy("account")

    def form_valid(self, form):
        messages.success(self.request, "Password updated successfully.")
        return super().form_valid(form)
