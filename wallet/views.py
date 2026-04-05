from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .models import Deposit, Withdrawal
from .models import Wallet, Transaction
from django.db.models import Sum

@login_required
def wallet_view(request):
    user = request.user  # ✅ define user
    wallet, created = Wallet.objects.get_or_create(user=user)

    transactions = Transaction.objects.filter(user=user).order_by("-created_at")

    withdrawals = Transaction.objects.filter(
        user=user,
        transaction_type="Withdraw"
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_deposit = Deposit.objects.filter(user=user, status='approved').aggregate(Sum('amount'))['amount__sum'] or 0
    total_withdrawal = Withdrawal.objects.filter(user=user, status='approved').aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        "wallet": wallet,
        "transactions": transactions,
        "withdrawals": withdrawals,
        "total_deposit": total_deposit,
        "total_withdrawal": total_withdrawal,
    }

    return render(request, "dashboard/wallet.html", context)  # ✅ pass full context
@login_required
def deposit_view(request):
    if request.method == "POST":

        if Deposit.objects.filter(user=request.user, status="pending").exists():
            messages.warning(request, "You already have a pending deposit. Please wait until it is processed.")
            return redirect("dashboard")

        amount = request.POST.get("amount")
        payment_method = request.POST.get("payment_method") 
        person_name = request.POST.get("person_name") # ✅ ADD THIS
        proof = request.FILES.get("proof")
        if not payment_method:
            messages.error(request, "Please select a payment method")
            return redirect("deposit")
        if not amount:
            messages.error(request, "Amount is required")
            return redirect("deposit")

        try:
            amount = Decimal(amount)
        except:
            messages.error(request, "Invalid amount")
            return redirect("deposit")

        if amount <= 0:
            messages.error(request, "Invalid amount")
            return redirect("deposit")

        Deposit.objects.create(
            user=request.user,
            amount=amount,
            payment_method=payment_method, 
            person_name=person_name, # ✅ FIXED
            proof=proof,
            status="pending"
        )

        messages.success(request, "Deposit request submitted successfully")
        return redirect("dashboard")

    deposits = Deposit.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "dashboard/deposit.html", {"deposits": deposits})
@login_required
def withdraw_view(request):

    if request.method == "POST":

        amount = request.POST.get("amount")
        wallet_address = request.POST.get("wallet_address")
        person_name = request.POST.get("person_name")

        # ✅ Validate ALL fields
        if not amount or not wallet_address or not person_name:
            messages.error(request, "All fields are required")
            return redirect("wallet:withdraw")

        try:
            amount = Decimal(amount)
        except:
            messages.error(request, "Invalid amount format")
            return redirect("wallet:withdraw")

        if amount <= 0:
            messages.error(request, "Invalid withdrawal amount")
            return redirect("wallet:withdraw")

        # ✅ Check user balance
        if amount > request.user.balance:
            messages.error(request, "Insufficient balance.")
            return redirect("wallet:withdraw")

        # ✅ Prevent multiple pending withdrawals
        pending = Withdrawal.objects.filter(
            user=request.user,
            status="pending"
        ).exists()

        if pending:
            messages.error(request, "You already have a pending withdrawal.")
            return redirect("wallet:withdraw")

        # ✅ Create withdrawal safely
        Withdrawal.objects.create(
            user=request.user,
            amount=amount,
            wallet_address=wallet_address,
            person_name=person_name,  # ✅ now guaranteed not empty
            status="pending"
        )

        messages.success(request, "Withdrawal request submitted.")
        return redirect("dashboard")

    return render(request, "dashboard/withdraw.html")
@login_required
def task_history(request):

    history = UserTask.objects.filter(
        user=request.user
    ).order_by("-completed_at")

    return render(request, "dashboard/task_history.html", {
        "history": history
    })    