from django.utils import timezone
from decimal import Decimal
from wallet.models import Transaction
from .models import UserVIP


def run_vip_profit():

    today = timezone.now()

    vip_users = UserVIP.objects.filter(
        active=True,
        end_date__gt=today
    )

    for vip in vip_users:

        user = vip.user
        percent = vip.plan.daily_profit_percent

        profit = user.balance * (Decimal(percent) / Decimal(100))

        user.balance += profit
        user.save()

        Transaction.objects.create(
            user=user,
            amount=profit,
            transaction_type="VIP Profit"
        )