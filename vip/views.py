from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import User
from vip.models import VIPPlan
from .models import UserVIP, VIPProfit, Task,UserTask
from wallet.models import Transaction  # For wallet transaction logging
from .tasks import run_vip_profit
from django.utils import timezone
def calculate_vip_profit(user):
    """
    Calculate missed daily VIP profit, add to user's wallet, and log it in VIPProfit.
    """
    user_vip = UserVIP.objects.filter(user=user, active=True).first()
    if not user_vip:
        return

    today = date.today()
    last_date = user_vip.last_profit_date
    missed_days = (today - last_date).days

    if missed_days <= 0:
        return

    # Daily profit calculation
    daily_profit = user_vip.vip_plan.price * (user_vip.vip_plan.daily_profit_percent / Decimal("100"))
    total_profit = daily_profit * missed_days

    # Add profit to user wallet balance
    user.balance += total_profit
    user.save()

    # Log profit in VIPProfit model
    VIPProfit.objects.create(
        user_vip=user_vip,
        user=user,
        amount=total_profit
    )

    # Optional: also log as a wallet transaction
    Transaction.objects.create(
        user=user,
        amount=total_profit,
        transaction_type=f"VIP Profit ({user_vip.vip_plan.name})"
    )

    # Update last profit date
    user_vip.last_profit_date = today
    user_vip.save()


@login_required
def vip_view(request):
    """
    Show the user's active VIP, days left, and available VIP plans.
    Only show valid upgrade options.
    """
    user = request.user

    # Calculate missed VIP profit before displaying
    calculate_vip_profit(user)

    current_vip = UserVIP.objects.filter(user=user, active=True).first()
    days_left = None
    daily_profit = None
    vip_level = 0 
    if current_vip:
        vip_level = current_vip.vip_plan.level
        # Days remaining
        if current_vip.end_date:
            days_left = max((current_vip.end_date - date.today()).days, 0)

        # Daily profit
        daily_profit = (current_vip.principal * current_vip.vip_plan.daily_profit_percent) / 100
        # Only allow upgrades to higher-level plans
        vip_plans = VIPPlan.objects.filter(level__gt=current_vip.vip_plan.level)
    else:
        # No active VIP: show all plans
        vip_plans = VIPPlan.objects.all()

    context = {
        "current_vip": current_vip,
        "days_left": days_left,
        "daily_profit": daily_profit,
        "vip_level": vip_level,
        "vip_plans": vip_plans
    }

    return render(request, "dashboard/vip.html", context)


@login_required
def buy_or_upgrade_vip(request, plan_id):
    """
    Buy a new VIP plan or upgrade an existing one.
    Handles unused principal value when upgrading.
    """
    user = request.user
    new_plan = get_object_or_404(VIPPlan, id=plan_id)

    # Get current active VIP
    current_vip = UserVIP.objects.filter(user=user, active=True).first()

    # Same plan check
    if current_vip and current_vip.vip_plan.id == new_plan.id:
        messages.warning(request, f"You already have an active {new_plan.name} VIP plan!")
        return redirect("vip:vip_view")

    # Downgrade prevention
    if current_vip and current_vip.vip_plan.level > new_plan.level:
        messages.error(request, f"You cannot downgrade from {current_vip.vip_plan.name} to {new_plan.name}!")
        return redirect("vip:vip_view")

    # Calculate unused value if upgrading
    unused_value = Decimal('0')
    if current_vip:
        today = date.today()
        days_used = (today - current_vip.start_date).days
        unused_days = max(current_vip.vip_plan.duration_days - days_used, 0)
        unused_value = (current_vip.principal / current_vip.vip_plan.duration_days) * unused_days

    total_cost = new_plan.price - unused_value
    if user.balance < total_cost:
        messages.error(request, "Insufficient balance to buy/upgrade this VIP plan.")
        return redirect("vip:vip_view")

    # Deduct from wallet
    user.balance -= total_cost
    user.save()

    # Deactivate current VIP
    if current_vip:
        current_vip.active = False
        current_vip.save()

    # Create new VIP
    UserVIP.objects.create(
        user=user,
        vip_plan=new_plan,
        principal=new_plan.price + unused_value,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=new_plan.duration_days),
        active=True
    )

    # Log transaction
    Transaction.objects.create(
        user=user,
        amount=total_cost,
        transaction_type=f"VIP Purchase/Upgrade ({new_plan.name})"
    )

    messages.success(request, f"You have successfully purchased/upgraded to {new_plan.name} VIP!")
    return redirect("vip:vip_view")


@login_required
def vip_profit_history(request):
    """
    Show the user's VIP profit history.
    """
    profits = VIPProfit.objects.filter(user=request.user).order_by("-date")
    context = {"profits": profits}
    return render(request, "dashboard/vip_profit_history.html", context)

@login_required
def daily_tasks(request):
    user = request.user
    today = timezone.now().date()

    # Get user's current VIP level
    current_vip = UserVIP.objects.filter(user=user, active=True).first()
    vip_level = current_vip.vip_plan.level if current_vip else 0

    # Get tasks available for this VIP level
    tasks = Task.objects.filter(vip_level=vip_level)

    # Initialize totals to avoid UnboundLocalError
    total_completed = 0
    total_limit = 0

    # Track progress per task
    for task in tasks:
        done_count = UserTask.objects.filter(
            user=user,
            task=task,
            completed_at=today
        ).count()

        # Attach directly to task for template use
        task.done = done_count
        task.left = max(task.daily_limit - done_count, 0)

        # Accumulate totals
        total_completed += done_count
        total_limit += task.daily_limit

    # Calculate progress safely
    progress = (total_completed / total_limit * 100) if total_limit > 0 else 0

    # Handle task completion
    if request.method == "POST":
        task_id = request.POST.get("task_id")
        proof = request.FILES.get("proof")
        task = get_object_or_404(Task, id=task_id)

        done_count = UserTask.objects.filter(
            user=user,
            task=task,
            completed_at=today
        ).count()

        if done_count >= task.daily_limit:
            messages.warning(request, "Task limit reached for today.")
            return redirect("vip:daily_tasks")
        last_task = UserTask.objects.filter(user=user).order_by('-created_at').first()
        if last_task and (timezone.now() - last_task.created_at < timedelta(seconds=15)):
            messages.warning(request, "Please wait a few seconds before next task.")
            return redirect("vip:daily_tasks")
        # Save task completion
        UserTask.objects.create(
            user=user,
            task=task,
            proof=proof,
            reward=task.reward,
            completed_at=today
        )

        # Add reward to user balance
        user.balance += task.reward
        user.save()

        # Record transaction
        Transaction.objects.create(
            user=user,
            amount=task.reward,
            transaction_type=f"Daily Task Reward ({task.name})"
        )

        messages.success(request, f"You earned {task.reward} Birr!")

        return redirect("vip:daily_tasks")

    # Prepare context for template
    context = {
        "tasks": tasks,
        "completed_count": total_completed,
        "total_limit": total_limit,
        "progress": progress,
    }

    return render(request, "dashboard/daily_tasks.html", {
        "tasks": tasks,
        "completed_count": total_completed,
        "total_limit": total_limit,
        "progress": progress,
    })
def vip_view_home(request):
    vip_plans = VIPPlan.objects.all().order_by("level")

    return render(request, "home.html", {
        "vip_plans": vip_plans
    })
@login_required
def task_history(request):

    history = UserTask.objects.filter(
        user=request.user
    ).order_by("-completed_at")

    return render(
        request,
        "dashboard/task_history.html",
        {"history": history}
    )