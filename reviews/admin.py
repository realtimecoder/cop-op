from django.contrib import admin
from .models import Review, WorkerFeedback


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('worker', 'customer', 'rating', 'created_at')
    list_filter = ('rating',)


@admin.register(WorkerFeedback)
class WorkerFeedbackAdmin(admin.ModelAdmin):
    list_display = ('worker', 'booking', 'cooperation_rating', 'created_at')
