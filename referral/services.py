from django.conf import settings
from accounts.models import User
from referral.models import ReferralCommission

# Commission percentages for each level
REFERRAL_LEVELS = [10, 5, 3, 2, 1]


def distribute_referral_commission(user, amount):

    current_referrer = user.referrer
    level = 0

    while current_referrer and level < len(REFERRAL_LEVELS):

        commission_percent = REFERRAL_LEVELS[level]
        commission_amount = (amount * commission_percent) / 100

        # Add commission to referrer balance
        current_referrer.balance += commission_amount
        current_referrer.referral_earnings += commission_amount
        current_referrer.save()

        # Save commission history
        ReferralCommission.objects.create(
            user=current_referrer,
            from_user=user,
            level=level + 1,
            amount=commission_amount
        )

        # Move to next upline
        current_referrer = current_referrer.referrer
        level += 1