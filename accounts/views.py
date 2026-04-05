from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model  
from datetime import date
from django.db.models import Sum  
import re
from .models import User, ReferralEarning  # your local models
from vip.models import VIPPlan, UserVIP
from vip.views import calculate_vip_profit
from vip.tasks import run_vip_profit
from user_profile.models import Profile

# ✅ Add this import for referral commissions
from referral.models import ReferralCommission  # ✅ import Profile

User = get_user_model()

def register_view(request):
    # BLOCK logged-in users
    if request.user.is_authenticated:
        messages.info(request, "You are already logged in.")
        return redirect("dashboard")

    # Get referral from POST or GET
    referral_code = request.POST.get("referral_code") or request.GET.get("ref")
    if referral_code:
        request.session['referral_code'] = referral_code

    if request.method == "POST":
        phone = request.POST.get("phone")
        password = request.POST.get("password")

        # CLEAN input
        if phone:
            phone = phone.strip().replace(" ", "")

        # VALIDATION
        if not phone or not password:
            messages.error(request, "All fields are required")
            return redirect("register")

        if not re.match(r"^0\d{9}$", phone):
            messages.error(request, "Phone number must start with 0 and be exactly 10 digits")
            return redirect("register")

        if len(password) < 4:
            messages.error(request, "Password must be at least 4 characters")
            return redirect("register")

        # CHECK duplicate in User table
        if User.objects.filter(phone=phone).exists():
            messages.error(request, "Phone already registered")
            return redirect("register")

        # GET referrer
        referrer = None
        saved_ref = request.session.get("referral_code")
        if saved_ref:
            referrer = User.objects.filter(referral_code=saved_ref).first()

        # CREATE USER safely
        try:
            user = User.objects.create_user(phone=phone, password=password)
        except IntegrityError:
            messages.error(request, "Phone already registered")
            return redirect("register")

        # ASSIGN referrer
        if referrer:
            user.referrer = referrer
            user.save()

        # ENSURE PROFILE exists
        profile, created = Profile.objects.get_or_create(user=user)
        profile.phone = phone
        profile.save()

        # CLEAR referral session
        if 'referral_code' in request.session:
            del request.session['referral_code']

        # LOGIN
        login(request, user)
        messages.success(request, "Account created successfully!")
        return redirect("dashboard")

    # GET request
    return render(request, "auth/register.html", {
        "referral_code": referral_code
    })

def vip_view(request):
    return render(request, 'dashboard/vip.html')


def home_view(request):
    vip_plans = VIPPlan.objects.all()
    return render(request, "home.html", {
        "vip_plans": vip_plans
    })


def login_view(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        password = request.POST.get("password")

        user = authenticate(
            request,
            phone=phone,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid phone or password")

    return render(request, "auth/login.html")


@login_required
def dashboard_view(request):
    user = request.user

    # calculate VIP profit
    calculate_vip_profit(user)

    # Get active VIP
    current_vip = UserVIP.objects.filter(user=user, active=True).first()
    if current_vip:
        vip_level = current_vip.vip_plan.level
        days_left = max((current_vip.end_date - date.today()).days, 0) if current_vip.end_date else 0
        progress_percent = int(
            ((current_vip.vip_plan.duration_days - days_left) / current_vip.vip_plan.duration_days) * 100
        )
    else:
        vip_level = 0
        days_left = 0
        progress_percent = 0

    # VIP plans
    vip_plans = VIPPlan.objects.all()

    # Referral link
    referral_link = request.build_absolute_uri(f"/register/?ref={user.referral_code}")

    # ✅ Real referral counting (only users with approved deposits)
    real_referrals = User.objects.filter(referrer=user, deposit__status="approved").distinct()
    total_referrals = real_referrals.count()

    # ✅ Referral earnings from ReferralCommission
    referral_earnings = ReferralCommission.objects.filter(user=user).aggregate(total=Sum("amount"))["total"] or 0

    # ✅ Phone number from profile
    phone_number = getattr(getattr(user, "profile", None), "phone", "N/A")

    # ✅ Recent members (latest 10 referral commissions)
    members = ReferralCommission.objects.filter(user=user).order_by("-created_at")[:10]

    context = {
        "balance": user.balance,
        "vip_level": vip_level,
        "current_vip": current_vip,
        "days_left": days_left,
        "progress_percent": progress_percent,
        "referral_code": user.referral_code,
        "referral_earnings": referral_earnings,
        "total_referrals": total_referrals,
        "vip_plans": vip_plans,
        "referral_link": referral_link,
        "members": members,
        "phone_number": phone_number,
    }

    return render(request, "dashboard/dashboard.html", context)


def logout_view(request):
    logout(request)
    return redirect("login")
