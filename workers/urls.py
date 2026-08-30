from django.urls import path
from . import views

app_name = 'workers'

urlpatterns = [
    path('for-service/<int:service_id>/', views.worker_list_for_service, name='worker_list_for_service'),
    path('profile/<int:worker_id>/', views.worker_public_profile, name='worker_public_profile'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('documents/', views.documents, name='documents'),
    path('dashboard/', views.my_dashboard, name='my_dashboard'),
    path('dashboard/edit/', views.edit_profile, name='edit_profile'),
    path('dashboard/request-category-change/', views.request_category_change, name='request_category_change'),
    path('dashboard/availability/', views.manage_availability, name='manage_availability'),
    path('dashboard/availability/<int:block_id>/unblock/', views.unblock_date, name='unblock_date'),
]
