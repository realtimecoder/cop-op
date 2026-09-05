from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('federation/dashboard/', views.federation_dashboard, name='federation_dashboard'),
    path('society/dashboard/', views.society_dashboard, name='society_dashboard'),
    path('society/invite-worker/', views.send_society_invite, name='send_society_invite'),
    path('pricing/', views.pricing_config, name='pricing_config'),
    path('pricing/service/<int:service_id>/', views.update_service_charge, name='update_service_charge'),
    path('workers/verification/', views.worker_verification_queue, name='worker_verification_queue'),
    path('workers/verification/<int:worker_id>/', views.verify_worker, name='verify_worker'),
    path('workers/claim-queue/', views.claim_workers_queue, name='claim_workers_queue'),
    path('workers/claim-queue/<int:worker_id>/', views.claim_worker, name='claim_worker'),
    path('workers/category-changes/', views.category_change_queue, name='category_change_queue'),
    path('workers/category-changes/<int:request_id>/', views.decide_category_change, name='decide_category_change'),
    path('complaints/', views.complaints_queue, name='complaints_queue'),
    path('complaints/<int:complaint_id>/resolve/', views.resolve_complaint, name='resolve_complaint'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<int:user_id>/', views.customer_detail, name='customer_detail'),
    path('workers/', views.worker_list, name='worker_list'),
    path('workers/<int:worker_id>/', views.worker_detail, name='worker_detail'),

    path('societies/', views.society_list, name='society_list'),
    path('societies/<int:society_id>/workers/', views.society_workers_list, name='society_workers_list'),
    path('societies/create/', views.society_create, name='society_create'),
    path('societies/<int:society_id>/assign-operator/', views.society_assign_operator, name='society_assign_operator'),
    path('societies/<int:society_id>/remove-operator/', views.society_remove_operator, name='society_remove_operator'),
    path('societies/<int:society_id>/toggle-fieldwork/', views.society_toggle_fieldwork, name='society_toggle_fieldwork'),
    path('societies/<int:society_id>/rename/', views.society_rename, name='society_rename'),
    path('societies/<int:society_id>/ban/', views.society_ban, name='society_ban'),
    path('societies/<int:society_id>/unban/', views.society_unban, name='society_unban'),
    path('societies/<int:society_id>/accept-resignation/', views.society_accept_resignation, name='society_accept_resignation'),
    path('societies/<int:society_id>/delete/', views.society_delete, name='society_delete'),
    path('societies/<int:society_id>/promote/', views.society_promote_to_federation, name='society_promote_to_federation'),

    path('federations/', views.federation_list, name='federation_list'),
    path('federations/create/', views.federation_create, name='federation_create'),
    path('federations/<int:federation_id>/assign-admin/', views.federation_assign_admin, name='federation_assign_admin'),
    path('federations/<int:federation_id>/rename/', views.federation_rename, name='federation_rename'),
    path('federations/<int:federation_id>/ban/', views.federation_ban, name='federation_ban'),
    path('federations/<int:federation_id>/unban/', views.federation_unban, name='federation_unban'),
    path('federations/<int:federation_id>/delete/', views.federation_delete, name='federation_delete'),
    path('federations/<int:federation_id>/commission/', views.federation_set_commission, name='federation_set_commission'),

    path('independent-societies/', views.independent_societies_list, name='independent_societies_list'),
    path('independent-societies/<int:society_id>/invite/', views.invite_society, name='invite_society'),
    path('federation-directory/', views.federation_directory, name='federation_directory'),
    path('federation-directory/<int:federation_id>/request-join/', views.request_join_federation, name='request_join_federation'),
    path('join-requests/', views.join_requests_queue, name='join_requests_queue'),
    path('join-requests/<int:request_id>/decide/', views.decide_join_request, name='decide_join_request'),
    path('manage-custom-pricing/', views.manage_custom_pricing, name='manage_custom_pricing'),
    path('manage-gov-opportunities/', views.manage_government_opportunities, name='manage_gov_opportunities'),

]
