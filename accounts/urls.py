from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_request, name='login'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('select-role/', views.select_role, name='select_role'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('profile/', views.profile, name='profile'),
    path('update-location/', views.update_location, name='update_location'),
    path('logout/', views.logout_view, name='logout'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
]
