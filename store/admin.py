# store/admin.py

from django.contrib import admin
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta
from django.urls import path
from django.shortcuts import render
from .models import Category, Product, Order, OrderItem, Voucher, Review
from django.contrib.admin import AdminSite # Import AdminSite
from django.contrib.auth.models import User, Group # Import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin # Import UserAdmin, GroupAdmin
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from allauth.account.models import EmailAddress

# --- TẠO ADMIN SITE TÙY CHỈNH ---
class MyAdminSite(AdminSite):
    # Thiết lập tiêu đề cho trang admin
    site_header = "Quản trị Shop Bóng Đá"
    site_title = "Admin Shop"
    index_title = "Dashboard" # Tiêu đề cho trang dashboard

    # Phương thức này ghi đè trang index mặc định
    def index(self, request, extra_context=None):
        """Hiển thị trang dashboard thay vì trang index mặc định."""

        # 1. Tính Doanh thu 7 ngày qua (đơn hoàn thành)
        seven_days_ago = timezone.now() - timedelta(days=7)
        # Dùng F expressions để tính (total_price - discount_amount) ở mức database
        revenue_data = Order.objects.filter(
            status='Hoàn thành',
            created_at__gte=seven_days_ago
        ).aggregate(
            total_revenue=Sum(F('total_price') - F('discount_amount')) # <-- SỬA LẠI THÀNH DÒNG NÀY
        )
        revenue_last_7_days = revenue_data['total_revenue'] or 0 # Lấy kết quả

        # 2. Đếm số Đơn hàng mới
        new_orders_count = Order.objects.filter(status='Mới').count()

        # 3. Tìm Top 5 Sản phẩm Bán chạy nhất (tính trên đơn hoàn thành)
        top_products = OrderItem.objects.filter(
            order__status='Hoàn thành' # Chỉ tính các item thuộc đơn hoàn thành
        ).values(
            'product__id', 'product__name' # Nhóm theo ID và Tên SP
        ).annotate(
            total_sold=Sum('quantity') # Tính tổng số lượng bán được cho mỗi SP
        ).order_by(
            '-total_sold' # Sắp xếp giảm dần theo số lượng bán
        )[:5] # Chỉ lấy 5 sản phẩm đầu tiên

        # Chuẩn bị context để gửi ra template
        context = {
            **super().each_context(request), # Lấy context mặc định của admin (ví dụ: user)
            'title': self.index_title, # Gửi tiêu đề trang
            'revenue_last_7_days': revenue_last_7_days,
            'new_orders_count': new_orders_count,
            'top_products': top_products,
            **(extra_context or {}),
        }

        # Render template dashboard đã tạo ở Bước 1
        return render(request, 'admin/dashboard.html', context)

# --- KHỞI TẠO ADMIN SITE MỚI ---
my_admin_site = MyAdminSite(name='myadmin')

# --- CÁC CLASS MODELADMIN (Giữ nguyên như cũ) ---
# (Định nghĩa cách hiển thị cho từng model trong admin)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_amount', 'min_purchase_amount', 'valid_from', 'valid_to', 'is_active')
    list_filter = ('is_active', 'valid_from', 'valid_to')
    search_fields = ('code',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price_at_purchase')

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'status', 'total_price', 'discount_amount', 'final_price', 'created_at')
    list_display_links = ('id', 'full_name', 'status')
    list_filter = ('created_at', 'status', 'voucher')
    inlines = [OrderItemInline]
    readonly_fields = ('user', 'full_name', 'email', 'phone', 'address', 'total_price', 'discount_amount', 'voucher', 'created_at')

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'product__name', 'comment')

# --- ĐĂNG KÝ CÁC MODEL VỚI ADMIN SITE MỚI ---
# Thay vì dùng admin.site.register, dùng my_admin_site.register
my_admin_site.register(Category)
my_admin_site.register(Product)
my_admin_site.register(Order, OrderAdmin)
my_admin_site.register(Voucher, VoucherAdmin)
my_admin_site.register(Review, ReviewAdmin)

# Đăng ký cả User và Group mặc định của Django
my_admin_site.register(User, UserAdmin)
my_admin_site.register(Group, GroupAdmin)

# Đăng ký các model của allauth để quản lý từ admin
my_admin_site.register(Site)
my_admin_site.register(SocialApp)
my_admin_site.register(SocialAccount)
my_admin_site.register(SocialToken)
my_admin_site.register(EmailAddress)