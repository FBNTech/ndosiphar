from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('utilisateurs/', views.user_list, name='user_list'),
    path('utilisateurs/nouveau/', views.user_create, name='user_create'),
    path('utilisateurs/<int:pk>/modifier/', views.user_edit, name='user_edit'),
    path('utilisateurs/<int:pk>/supprimer/', views.user_delete, name='user_delete'),
]
