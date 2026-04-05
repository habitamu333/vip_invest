from django.utils import timezone
from vip.models import UserVIP
from wallet.models import Transaction


def daily_vip_profit():

    active_vips = UserVIP.objects.filter(
        active=True,
        end_date__gte=timezone.now()
    )

    for user_vip in active_vips:

        user = user_vip.user
        profit = user_vip.vip_plan.daily_profit

        # Add profit to user balance
        user.balance += profit
        user.save()

        # Save transaction history
        Transaction.objects.create(
            user=user,
            amount=profit,
            transaction_type="VIP Profit"
        )