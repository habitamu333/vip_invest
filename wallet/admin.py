from django.contrib import admin
from .models import Deposit, Withdrawal, Transaction
from accounts.models import User
from django.utils.html import format_html


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'payment_method', 'status', 'created_at', 'proof_preview')
    list_filter = ('status', 'payment_method')
    search_fields = ('user__username',)
    readonly_fields = ('proof_preview',)

    # This function MUST be indented correctly inside the class
    def proof_preview(self, obj):
        if obj.proof:  # Make sure this is indented inside the function
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" width="100" style="object-fit:cover;"/></a>',
                obj.proof.url,
                obj.proof.url
            )
        return "-"
    proof_preview.short_description = 'Payment Proof'


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):

    list_display = ("user", "amount", "person_name", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username",)

    def save_model(self, request, obj, form, change):

        if change:
            old = Withdrawal.objects.get(id=obj.id)

            # If admin approves withdrawal
            if old.status != "approved" and obj.status == "approved":

                user = obj.user

                if user.balance >= obj.amount:
                    user.balance -= obj.amount
                    user.save()

                    # Create transaction record
                    Transaction.objects.create(
                        user=user,
                        amount=obj.amount,
                        transaction_type="withdraw"
                    )

        super().save_model(request, obj, form, change)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):

    list_display = ("user", "amount", "transaction_type", "created_at")
    list_filter = ("transaction_type",)
    search_fields = ("user__username",)