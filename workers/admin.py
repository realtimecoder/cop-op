from django.contrib import admin
from .models import (Society, WorkerProfile, WorkerDocument, WorkerServiceOffering,
                      Federation, FederationJoinRequest)


@admin.register(Federation)
class FederationAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'admin_user', 'commission_percent', 'is_banned', 'is_active')
    list_filter = ('is_banned', 'is_active')


@admin.register(FederationJoinRequest)
class FederationJoinRequestAdmin(admin.ModelAdmin):
    list_display = ('society', 'federation', 'initiated_by', 'status', 'created_at')
    list_filter = ('status', 'initiated_by')


class DocumentInline(admin.TabularInline):
    model = WorkerDocument
    extra = 0


class OfferingInline(admin.TabularInline):
    model = WorkerServiceOffering
    extra = 0


@admin.register(Society)
class SocietyAdmin(admin.ModelAdmin):
    list_display = ('name', 'federation', 'city', 'operator', 'is_banned', 'is_active')
    list_filter = ('federation', 'is_banned', 'is_active')


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'society', 'verification_status', 'skill_grade', 'average_rating',
                     'completed_jobs', 'payout_percentage', 'is_available_now')
    list_filter = ('verification_status', 'skill_grade', 'society')
    search_fields = ('user__first_name', 'user__last_name', 'user__phone_number')
    filter_horizontal = ('categories',)
    inlines = [DocumentInline, OfferingInline]
    list_editable = ('payout_percentage', 'is_available_now')


@admin.register(WorkerDocument)
class WorkerDocumentAdmin(admin.ModelAdmin):
    list_display = ('worker', 'doc_type', 'is_approved', 'uploaded_at')
    list_filter = ('doc_type', 'is_approved')
