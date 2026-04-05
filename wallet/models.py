from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from accounts.utils import give_referral_commission
class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{getattr(self.user, 'phone', 'User')} Wallet"
class Withdrawal(models.Model):

    STATUS = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    wallet_address = models.CharField(max_length=255, default="unknown")  

    person_name = models.CharField(max_length=100, default="unknown")

    status = models.CharField(max_length=10, choices=STATUS, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

class Transaction(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    transaction_type = models.CharField(
        max_length=50
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user} - {self.transaction_type} - {self.amount}"
    
class Deposit(models.Model):

    STATUS = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    PAYMENT_METHODS = (
        ("CBE", "CBE"),
        ("TeleBirr", "Tele Birr"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHODS,
        default="TeleBirr"  # ✅ FIXED
    )

    person_name = models.CharField(max_length=100, default="unknown")

    proof = models.ImageField(upload_to="deposits/", blank=True, null=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        if self.pk:
            old = Deposit.objects.filter(pk=self.pk).first()

            if old and old.status != "approved" and self.status == "approved":

                user = self.user

                # ✅ Add balance
                user.balance += self.amount
                user.save()

                # ✅ Save transaction
                Transaction.objects.create(
                    user=user,
                    amount=self.amount,
                    transaction_type="Deposit"
                )

                # ✅ FIXED referral call
                give_referral_commission(user, self.amount)

        super().save(*args, **kwargs)