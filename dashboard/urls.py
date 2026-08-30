from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('pricing/', views.pricing_config, name='pricing_config'),
    path('pricing/service/<int:service_id>/', views.update_service_charge, name='update_service_charge'),
    path('workers/verification/', views.worker_verification_queue, name='worker_verification_queue'),
    path('workers/verification/<int:worker_id>/', views.verify_worker, name='verify_worker'),
    path('workers/category-changes/', views.category_change_queue, name='category_change_queue'),
    path('workers/category-changes/<int:request_id>/', views.decide_category_change, name='decide_category_change'),
    path('complaints/', views.complaints_queue, name='complaints_queue'),
    path('complaints/<int:complaint_id>/resolve/', views.resolve_complaint, name='resolve_complaint'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<int:user_id>/', views.customer_detail, name='customer_detail'),
    path('workers/', views.worker_list, name='worker_list'),
    path('workers/<int:worker_id>/', views.worker_detail, name='worker_detail'),
]
