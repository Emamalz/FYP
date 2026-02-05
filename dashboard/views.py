import os
import json
import pandas as pd

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib import messages
from django.contrib.auth import logout
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

    # -----------------------
    # TIMESTAMP (ROBUST)
    # -----------------------
    df["transaction_timestamp"] = pd.to_datetime(
        df["transaction_timestamp"],
        dayfirst=True,
        errors="coerce"
    )

    # fallback to unix_time
    missing_ts = df["transaction_timestamp"].isna()
    if "unix_time" in df.columns:
        df.loc[missing_ts, "transaction_timestamp"] = pd.to_datetime(
            df.loc[missing_ts, "unix_time"],
            unit="s",
            errors="coerce"
        )

    df = df.dropna(subset=["transaction_timestamp"])
    df["transaction_timestamp"] = df["transaction_timestamp"].dt.floor("s")

    # -----------------------
    # AMOUNT
    # -----------------------
    df["transaction_amount"] = pd.to_numeric(
        df["transaction_amount"], errors="coerce"
    ) / 100

    # -----------------------
    # FRAUD LABEL (FINAL FIX)
    # -----------------------
    df["fraud_label"] = df["fraud_label"].apply(
        lambda x: True if str(x).strip().lower() == "true" else False
    )

    # -----------------------
    # DATE FILTERS (FULL DAY SAFE)
    # -----------------------
    start_date = request.GET.get("from")
    end_date = request.GET.get("to")

    if start_date:
        start_dt = pd.to_datetime(start_date).normalize()
        df = df[df["transaction_timestamp"] >= start_dt]

    if end_date:
        end_dt = pd.to_datetime(end_date).normalize() + pd.Timedelta(days=1)
        df = df[df["transaction_timestamp"] < end_dt]

    # -----------------------
    # FRAUD TOGGLE (IMPORTANT)
    # -----------------------
    fraud_only = request.GET.get("fraud")
    if fraud_only == "1":
        df = df[df["fraud_label"] == True]

    # -----------------------
    # SEARCH (SERVER-SIDE, BEFORE PAGINATION)
    # -----------------------
    search = request.GET.get("search")
    if search:
        search = search.lower()
        df = df[
            df["transaction_id"].str.lower().str.contains(search, na=False)
            | df["customer_id"].str.lower().str.contains(search, na=False)
        ]

    # -----------------------
    # SORT (AFTER ALL FILTERS)
    # -----------------------
    df = df.sort_values("transaction_timestamp", ascending=False)

    # -----------------------
    # PAGINATION (LAST STEP)
    # -----------------------
    page_size = 50
    page = int(request.GET.get("page", 1))

    total_rows = len(df)
    total_pages = max((total_rows - 1) // page_size + 1, 1)

    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size

    page_df = df.iloc[start:end]

    # -----------------------
    # CHART (MATCHES FILTERED DATA)
    # -----------------------
    grouped = (
        df
        .set_index("transaction_timestamp")
        .resample("D")
        .agg(
            total_transactions=("transaction_id", "count"),
            fraud_transactions=("fraud_label", "sum")
        )
    )

    grouped = grouped[grouped["total_transactions"] > 0]

    chart_labels = grouped.index.strftime("%Y-%m-%d").tolist()
    total_tx_data = grouped["total_transactions"].tolist()
    fraud_tx_data = grouped["fraud_transactions"].tolist()

    context = {
        "transactions": page_df.to_dict(orient="records"),

        "page": page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,

        "chart_labels": json.dumps(chart_labels),
        "total_tx_data": json.dumps(total_tx_data),
        "fraud_tx_data": json.dumps(fraud_tx_data),

        "from_date": start_date or "",
        "to_date": end_date or "",
        "fraud_only": fraud_only == "1",
        "search": search or "",
    }

    return render(request, "dashboard/transactions.html", context)

# ===========================
# DASHBOARD (REAL APP DASHBOARD)
# ===========================
@login_required
def dashboard(request):
    total_transactions = Transaction.objects.count()
    fraud_count = Transaction.objects.filter(fraud_label=True).count()
    total_volume = (
        Transaction.objects.aggregate(total=Sum("transaction_amount"))["total"] or 0
    )

    return render(request, "dashboard/index.html", {
        "total_transactions": total_transactions,
        "fraud_count": fraud_count,
        "total_volume": round(total_volume, 2),
    })


# ===========================
# LANDING / MARKETING PAGE
# ===========================
def home(request):
    return render(request, "dashboard/home.html")


# ===========================
# OTHER PAGES
# ===========================
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


# ===========================
# AUTH
# ===========================
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


def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("home")
