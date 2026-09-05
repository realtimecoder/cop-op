from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('how-it-works/', views.how_it_works, name='how_it_works'),
    path('government-opportunities/', views.government_opportunities, name='government_opportunities'),
    path('government-opportunities/apply/<int:project_id>/', views.apply_government_opportunity, name='apply_government_opportunity'),
    path('contact/', views.contact, name='contact'),
    path('pricing-policy/', views.pricing_policy, name='pricing_policy'),
]
