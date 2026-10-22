from django.urls import path

from . import views as V

urlpatterns = [
    path("health/", V.HealthView.as_view()),
    path("auth/demo-profiles/", V.DemoProfilesView.as_view()),
    path("auth/demo-login/", V.DemoLoginView.as_view()),
    path("auth/me/", V.MeView.as_view()),
    path("auth/logout/", V.LogoutView.as_view()),
    path("company/", V.CompanyView.as_view()),
    path("products/", V.ProductsView.as_view()),
    path("products/<str:product_id>/", V.ProductView.as_view()),
    path("news/", V.NewsView.as_view()),
    path("news/<int:news_id>/", V.NewsDetailView.as_view()),
    path("scoring/pre-predict/", V.PrePredictView.as_view()),
    path("applications/", V.ApplicationsView.as_view()),
    path("applications/<uuid:application_id>/", V.ApplicationView.as_view()),
    path("applications/<uuid:application_id>/submit/", V.SubmitView.as_view()),
    path("applications/<uuid:application_id>/cancel/", V.CancelView.as_view()),
    path(
        "applications/<uuid:application_id>/history/", V.HistoryView.as_view()
    ),
    path(
        "applications/<uuid:application_id>/scoring/",
        V.ClientScoringView.as_view(),
    ),
    path("applications/<uuid:application_id>/offer/", V.OfferView.as_view()),
    path(
        "applications/<uuid:application_id>/offers/<uuid:offer_id>/accept/",
        V.AcceptOfferView.as_view(),
    ),
    path(
        "applications/<uuid:application_id>/offers/<uuid:offer_id>/decline/",
        V.DeclineOfferView.as_view(),
    ),
    path(
        "applications/<uuid:application_id>/documents/",
        V.DocumentsView.as_view(),
    ),
    path(
        (
            "applications/<uuid:application_id>/documents/<uuid"
            ":document_id>/download/"
        ),
        V.DocumentDownloadView.as_view(),
    ),
    path("applications/<uuid:application_id>/sign/", V.SignView.as_view()),
    path(
        "applications/<uuid:application_id>/info-request/",
        V.InfoRequestView.as_view(),
    ),
    path(
        (
            "applications/<uuid:application_id>/info-requests/<"
            "uuid:info_request_id>/respond/"
        ),
        V.InfoResponseView.as_view(),
    ),
    path("bank/applications/", V.BankQueueView.as_view()),
    path(
        "bank/applications/<uuid:application_id>/",
        V.BankApplicationView.as_view(),
    ),
    path(
        "bank/applications/<uuid:application_id>/decisions/",
        V.BankDecisionsView.as_view(),
    ),
    path(
        "bank/applications/<uuid:application_id>/history/",
        V.BankHistoryView.as_view(),
    ),
    path(
        "bank/applications/<uuid:application_id>/documents/",
        V.BankDocumentsView.as_view(),
    ),
]
