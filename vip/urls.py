from django.urls import path
from . import views

app_name = 'vip'  # make sure this is set!

urlpatterns = [
    path('', views.vip_view_home, name='home'),  # ✅ FIXED
    path('dashboard/vip/', views.vip_view, name='vip_view'),
    path('buy-or-upgrade/<int:plan_id>/', views.buy_or_upgrade_vip, name='buy_or_upgrade_vip'),
    path('profit-history/', views.vip_profit_history, name='vip_profit_history'),
    path("daily-tasks/", views.daily_tasks, name="daily_tasks"),
    path("task-history/", views.task_history, name="task_history"),
]