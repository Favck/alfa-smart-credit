from django.urls import path

from . import completion as C
from . import pipeline as P
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
    path("scoring/pre-predict/", P.PrePredictView.as_view()),
    path("applications/", P.ApplicationsView.as_view()),
    path("applications/<uuid:application_id>/", P.ApplicationView.as_view()),
    path("applications/<uuid:application_id>/submit/", P.SubmitView.as_view()),
    path("applications/<uuid:application_id>/cancel/", P.CancelView.as_view()),
    path(
        "applications/<uuid:application_id>/history/", P.HistoryView.as_view()
    ),
    path(
        "applications/<uuid:application_id>/scoring/",
        P.ClientScoringView.as_view(),
    ),
    path("applications/<uuid:application_id>/offer/", C.OfferView.as_view()),
    path(
        "applications/<uuid:application_id>/offers/<uuid:offer_id>/accept/",
        C.AcceptOfferView.as_view(),
    ),
    path(
        "applications/<uuid:application_id>/offers/<uuid:offer_id>/decline/",
        C.DeclineOfferView.as_view(),
    ),
    path(
        "applications/<uuid:application_id>/documents/",
        C.DocumentsView.as_view(),
    ),
    path(
        (
            "applications/<uuid:application_id>/documents/<uuid"
            ":document_id>/download/"
        ),
        C.DocumentDownloadView.as_view(),
    ),
    path("applications/<uuid:application_id>/sign/", C.SignView.as_view()),
    path(
        "applications/<uuid:application_id>/info-request/",
        C.InfoRequestView.as_view(),
    ),
    path(
        (
            "applications/<uuid:application_id>/info-requests/<"
            "uuid:info_request_id>/respond/"
        ),
        C.InfoResponseView.as_view(),
    ),
    path("bank/applications/", P.BankQueueView.as_view()),
    path(
        "bank/applications/<uuid:application_id>/",
        P.BankApplicationView.as_view(),
    ),
    path(
        "bank/applications/<uuid:application_id>/decisions/",
        P.BankDecisionsView.as_view(),
    ),
    path(
        "bank/applications/<uuid:application_id>/history/",
        P.BankHistoryView.as_view(),
    ),
    path(
        "bank/applications/<uuid:application_id>/documents/",
        C.BankDocumentsView.as_view(),
    ),
]
