from django.contrib import admin
from .models import (
    CommunityChannel, CommunityMessage, WageSuggestion,
    FairPayRecommendation, GovernmentOpportunity, OpportunityApplication
)

@admin.register(CommunityChannel)
class CommunityChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_announcement', 'category')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(CommunityMessage)
class CommunityMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(WageSuggestion)
class WageSuggestionAdmin(admin.ModelAdmin):
    list_display = ('worker', 'category', 'suggested_wage', 'unit')

@admin.register(FairPayRecommendation)
class FairPayRecommendationAdmin(admin.ModelAdmin):
    list_display = ('category', 'min_wage', 'max_wage', 'unit_value', 'is_active')

@admin.register(GovernmentOpportunity)
class GovernmentOpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'category', 'status', 'is_published')
    list_filter = ('status', 'category', 'is_published')
    search_fields = ('title', 'organization')

@admin.register(OpportunityApplication)
class OpportunityApplicationAdmin(admin.ModelAdmin):
    list_display = ('opportunity', 'worker', 'status', 'applied_at')
    list_filter = ('status', 'opportunity')
