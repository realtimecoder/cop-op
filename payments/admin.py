from django.contrib import admin
from .models import Payment, Invoice


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reference_id', 'booking', 'method', 'status', 'amount', 'worker_payout', 'cooperative_fee')
    list_filter = ('method', 'status')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'payment', 'generated_at')
