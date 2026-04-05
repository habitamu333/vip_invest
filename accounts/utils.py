from decimal import Decimal

REFERRAL_LEVELS = {
    1: Decimal("0.10"),
    2: Decimal("0.05"),
    3: Decimal("0.03"),
    4: Decimal("0.02"),
    5: Decimal("0.01"),
    6: Decimal("0.01"),
    7: Decimal("0.005"),
    8: Decimal("0.005"),
    9: Decimal("0.005"),
}

def give_referral_commission(user, amount):
    from referral.models import ReferralCommission
    from wallet.models import Transaction  # ✅ add this import here

    current_user = user

    for level in range(1, 10):
        referrer = current_user.referrer
        if not referrer:
            break

        percentage = REFERRAL_LEVELS.get(level, Decimal("0"))
        commission = Decimal(amount) * percentage

        if commission > 0:
            # Update balances
            referrer.balance += commission
            referrer.referral_earnings += commission
            referrer.save()

            # Create commission record
            ReferralCommission.objects.create(
                user=referrer,
                from_user=user,
                level=level,
                amount=commission
            )

            # ✅ Add to transaction history
            Transaction.objects.create(
                user=referrer,
                amount=commission,
                transaction_type="Referral"
            )

        current_user = referrer