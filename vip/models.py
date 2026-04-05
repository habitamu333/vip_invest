from django.db import models
from django.conf import settings
from datetime import date, timedelta
from decimal import Decimal
from django.utils.timezone import now
User = settings.AUTH_USER_MODEL

class VIPPlan(models.Model):
    name = models.CharField(max_length=50)
    level = models.IntegerField()  # Silver=1, Gold=2, Diamond=3, etc.
    price = models.DecimalField(max_digits=12, decimal_places=2)
    daily_profit_percent = models.DecimalField(max_digits=5, decimal_places=2, default=3.3)
    duration_days = models.IntegerField(default=30)

    def __str__(self):
        return f"{self.name} - ${self.price}"


class UserVIP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_vips")
    vip_plan = models.ForeignKey(VIPPlan, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    last_profit_date = models.DateField(default=date.today)
    principal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.phone} - {self.vip_plan.name}"

    @property
    def days_used(self):
        return max((date.today() - self.start_date).days, 0)

    @property
    def days_remaining(self):
        if self.end_date:
            return max((self.end_date - date.today()).days, 0)
        return self.vip_plan.duration_days - self.days_used

    def upgrade_to(self, new_plan):
        """
        Upgrade this VIP plan to a new VIPPlan mid-way.
        Ensures plan type and level are considered.
        """
        today = date.today()

        # 1️⃣ Prevent upgrade to same or lower plan
        if self.vip_plan.name == new_plan.name:
            raise ValueError(f"You already have an active {self.vip_plan.name} VIP plan!")
        if self.vip_plan.level > new_plan.level:
            raise ValueError(f"Cannot downgrade to a lower VIP plan ({new_plan.name})!")

        # 2️⃣ Calculate unused days and pro-rata value
        unused_days = max(self.vip_plan.duration_days - self.days_used, 0)
        unused_value = (self.principal / self.vip_plan.duration_days) * unused_days

        # 3️⃣ Deactivate current plan
        self.active = False
        self.save()

        # 4️⃣ Create new VIP plan with pro-rata principal
        new_principal = new_plan.price + unused_value
        new_user_vip = UserVIP.objects.create(
            user=self.user,
            vip_plan=new_plan,
            principal=new_principal,
            active=True,
            start_date=today,
            end_date=today + timedelta(days=new_plan.duration_days),
            last_profit_date=today
        )
        return new_user_vip


class VIPProfit(models.Model):
    """
    Stores the VIP profit credited daily.
    """
    user_vip = models.ForeignKey(UserVIP, on_delete=models.CASCADE, related_name="profits")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.phone} - ${self.amount} on {self.date}"
    
class Task(models.Model):
    """
    Admin creates tasks
    """
    name = models.CharField(max_length=100)
    vip_level = models.IntegerField()
    link = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)
    reward = models.DecimalField(max_digits=10, decimal_places=2)
    daily_limit = models.IntegerField(default=1)
    icon = models.CharField(max_length=50, default="bi-check-circle")

    def __str__(self):
        return f"{self.name} (VIP {self.vip_level})"


class UserTask(models.Model):
    """
    Stores completed tasks
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateField(default=date.today)
    reward = models.DecimalField(max_digits=10, decimal_places=2)
    proof = models.ImageField(upload_to='proofs/', blank=True, null=True)
    def __str__(self):
        return f"{self.user} - {self.task.name}"   