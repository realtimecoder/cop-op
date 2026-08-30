from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.category_list, name='category_list'),
    path('<slug:slug>/', views.category_detail, name='category_detail'),
    path('<slug:category_slug>/<slug:service_slug>/', views.service_detail, name='service_detail'),
]
