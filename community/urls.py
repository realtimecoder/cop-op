from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    path('global-chat/', views.global_chat, name='global_chat'),
    path('dashboard/', views.community_dashboard, name='dashboard'),
    path('manage/', views.manage_communities, name='manage_communities'),
    path('memberships/', views.manage_memberships, name='manage_memberships'),
    path('membership/<int:membership_id>/<str:status>/', views.update_membership_status, name='update_membership'),
    path('join/<int:community_id>/', views.request_join_community, name='request_join'),
    path('hub/<slug:community_slug>/', views.community_index, name='index'),
    path('hub/<slug:community_slug>/<slug:channel_slug>/', views.community_channel, name='channel'),
    path('fair-pay/', views.fair_pay_index, name='fair_pay'),
    path('fair-pay/submit/', views.fair_pay_submit, name='fair_pay_submit'),
    path('government/', views.gov_hub_index, name='gov_hub'),
    path('government/<int:opp_id>/', views.gov_opportunity_detail, name='gov_detail'),
    path('government/<int:opp_id>/apply/', views.gov_apply, name='gov_apply'),
]
