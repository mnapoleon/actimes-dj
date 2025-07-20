from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('session/<int:pk>/', views.SessionDetailView.as_view(),
         name='session_detail'),
    path('session/<int:pk>/edit/', views.SessionEditView.as_view(),
         name='session_edit'),
    path('session/<int:pk>/delete/', views.SessionDeleteView.as_view(),
         name='session_delete'),
    path('session/<int:session_pk>/delete-driver/<str:driver_name>/', 
         views.delete_driver_from_session, name='delete_driver'),
    path('api/session/<int:pk>/', views.session_data_api,
         name='session_api'),
]
