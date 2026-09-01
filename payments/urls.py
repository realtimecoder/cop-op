from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('wallet/', views.wallet_dashboard, name='wallet_dashboard'),
    path('withdraw/', views.withdraw_funds, name='withdraw_funds'),
]
