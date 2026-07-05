from django.urls import path
from . import views

urlpatterns = [
    # Configuración IA (proveedor + key + modelo)
    path('config/', views.AIConfigView.as_view(), name='ai_config'),
    path('config/test/', views.AITestView.as_view(), name='ai_config_test'),
    # Multi-proveedor (fallback) + prompts editables
    path('providers/', views.AIProvidersView.as_view(), name='ai_providers'),
    path('prompts/', views.AIPromptsView.as_view(), name='ai_prompts'),
    # Features IA
    path('event-description/', views.EventDescriptionView.as_view(), name='ai_event_description'),
    path('event-banner/', views.EventBannerView.as_view(), name='ai_event_banner'),
    # Features IA (placeholders Fase 8-12)
    path('copilot/body/', views.CopilotBodyView.as_view(), name='ai_copilot_body'),
    path('excel/map-columns/', views.ExcelMapColumnsView.as_view(), name='ai_excel_map'),
    path('voice/extract/', views.VoiceExtractView.as_view(), name='ai_voice_extract'),
    path('insights/dashboard/', views.InsightsDashboardView.as_view(), name='ai_insights_dashboard'),
    path('recommendations/<str:email>/', views.RecommendationsView.as_view(), name='ai_recommendations'),
]
