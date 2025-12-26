# core/urls.py
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static


from store.views import (
    home, product_detail, add_to_cart, cart_view, 
    update_cart, checkout, 
    order_success,
    landing_page
)
# THÊM IMPORT MỚI TỪ APP 'users'
from users.views import (
    register_view, login_view, logout_view, 
    order_history_view,
    order_detail_view, profile_view, verify_email_confirm
)
from store.admin import my_admin_site
urlpatterns = [
    path('admin/', my_admin_site.urls),  # Sử dụng custom admin site
    path('home/', home, name='home'),
    path('', landing_page, name='landing_page'),
    path('product/<int:product_id>/', product_detail, name='product_detail'),
    path('add-to-cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', cart_view, name='cart_view'),
    path('update-cart/<int:product_id>/', update_cart, name='update_cart'),
    path('checkout/', checkout, name='checkout'),
    path('order-success/', order_success, name='order_success'),
    # URL cho user registration, login, logout
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('order-history/', order_history_view, name='order_history'),
    path('order-detail/<int:order_id>/', order_detail_view, name='order_detail'),
    path('profile/', profile_view, name='profile'),
    path('verify-email/<uidb64>/<token>/', verify_email_confirm, name='verify_email_confirm'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)