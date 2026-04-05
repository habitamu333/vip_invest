from django.contrib import admin
from .models import VIPPlan, UserVIP
from .models import Task, UserTask

@admin.register(VIPPlan)
class VIPPlanAdmin(admin.ModelAdmin):

    list_display = ("name", "level", "price", "daily_profit_percent", "duration_days")


@admin.register(UserVIP)
class UserVIPAdmin(admin.ModelAdmin):

    list_display = ("user", "vip_plan", "start_date", "end_date", "active")
    admin.site.register(Task)
    admin.site.register(UserTask)