from django.contrib import admin
from .models import Society, WorkerProfile, WorkerDocument, WorkerServiceOffering


class DocumentInline(admin.TabularInline):
    model = WorkerDocument
    extra = 0


class OfferingInline(admin.TabularInline):
    model = WorkerServiceOffering
    extra = 0


@admin.register(Society)
class SocietyAdmin(admin.ModelAdmin):
    list_display = ('name', 'federation_name', 'city')


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
