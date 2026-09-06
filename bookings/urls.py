from django.urls import path
from . import views, bulk_views

app_name = 'bookings'

urlpatterns = [
    path('request/<int:service_id>/', views.booking_request, name='booking_request'),
    path('choice/<int:request_id>/', views.booking_choice, name='booking_choice'),
    path('finalize/<int:request_id>/<int:worker_id>/', views.finalize_booking_from_request, name='finalize_booking_from_request'),
    path('new/<int:service_id>/<int:worker_id>/', views.create_booking, name='create_booking'),
    path('emergency/<int:service_id>/', views.create_emergency_booking, name='create_emergency_booking'),
    path('availability/<int:worker_id>/', views.worker_availability_json, name='worker_availability'),
    path('mine/', views.my_bookings, name='my_bookings'),
    path('<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('<int:booking_id>/status/', views.booking_status_json, name='booking_status_json'),
    path('<int:booking_id>/action/<str:action>/', views.worker_action, name='worker_action'),
    path('<int:booking_id>/confirm/', views.confirm_completion, name='confirm_completion'),
    path('<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('<int:booking_id>/pay/', views.make_payment, name='make_payment'),
    path('<int:booking_id>/pay/callback/', views.razorpay_callback, name='razorpay_callback'),
    path('<int:booking_id>/review/', views.submit_review, name='submit_review'),
    path('<int:booking_id>/complaint/', views.file_complaint, name='file_complaint'),

    # SOS (Broadcast-and-Claim) flow
    path('sos/request/<int:service_id>/', views.request_sos, name='request_sos'),
    path('sos/accept/<int:booking_id>/', views.accept_sos, name='accept_sos'),
    path('sos/waiting/<int:booking_id>/', views.sos_waiting, name='sos_waiting'),
    path('sos/available/', views.available_sos_requests, name='available_sos_requests'),

    # Institution flow: bulk/multiple-worker requests -> cooperative assignment -> completion
    path('bulk/new/', bulk_views.create_bulk_request, name='create_bulk_request'),
    path('bulk/mine/', bulk_views.my_bulk_requests, name='my_bulk_requests'),
    path('bulk/<int:request_id>/', bulk_views.bulk_request_detail, name='bulk_request_detail'),
    path('bulk/<int:request_id>/cancel/', bulk_views.cancel_bulk_request, name='cancel_bulk_request'),
    path('bulk/<int:request_id>/complete/', bulk_views.confirm_bulk_completion, name='confirm_bulk_completion'),
    path('bulk/queue/', bulk_views.bulk_request_queue, name='bulk_request_queue'),
    path('bulk/<int:request_id>/claim/', bulk_views.claim_bulk_request, name='claim_bulk_request'),
    path('bulk/<int:request_id>/assign/', bulk_views.assign_bulk_workers, name='assign_bulk_workers'),
    path('bulk/<int:request_id>/start/', bulk_views.start_bulk_work, name='start_bulk_work'),
]
