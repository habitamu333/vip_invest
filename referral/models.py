from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class ReferralCommission(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="referral_income"
    )

    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="generated_commission"
    )

    level = models.IntegerField()

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):  # ✅ FIXED
        return f"{self.user} earned {self.amount} from {self.from_user} (Level {self.level})"