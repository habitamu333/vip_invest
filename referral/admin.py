from django.contrib import admin
from .models import ReferralCommission


@admin.register(ReferralCommission)
class ReferralCommissionAdmin(admin.ModelAdmin):

    list_display = ("user", "from_user", "level", "amount", "created_at")