from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

# --- CÁC LỰA CHỌN TRẠNG THÁI ---
ORDER_STATUS_CHOICES = [
    ('Mới', 'Mới'),
    ('Đang xử lý', 'Đang xử lý'),
    ('Đang giao', 'Đang giao'),
    ('Hoàn thành', 'Hoàn thành'),
    ('Đã hủy', 'Đã hủy'),
]

# --- MODEL CATEGORY (Như cũ) ---
class Category(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

# --- MODEL PRODUCT (Như cũ) ---
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    image = models.URLField(max_length=1024, blank=True, null=True)
    stock = models.IntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    
    def __str__(self):
        return self.name

# --- MODEL VOUCHER (Như cũ) ---
class Voucher(models.Model):
    code = models.CharField(max_length=50, unique=True, help_text="Mã giảm giá, ví dụ: GIAM10")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=0, help_text="Số tiền giảm (VND)")
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=0, default=0, help_text="Số tiền mua tối thiểu để áp dụng")
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def is_valid(self, total_price):
        now = timezone.now()
        if not self.is_active:
            return False, "Mã giảm giá này đã bị vô hiệu hóa."
        if now < self.valid_from:
            return False, "Mã giảm giá này chưa đến ngày sử dụng."
        if now > self.valid_to:
            return False, "Mã giảm giá này đã hết hạn."
        if total_price < self.min_purchase_amount:
            return False, f"Đơn hàng phải đạt tối thiểu {self.min_purchase_amount} VNĐ để dùng mã này."
        return True, "Hợp lệ"

    def __str__(self):
        return f"{self.code} (Giảm {self.discount_amount} VNĐ)"

# --- MODEL ORDER (Như cũ) ---
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    
    total_price = models.DecimalField(max_digits=10, decimal_places=0, help_text="Tổng tiền ban đầu")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='Mới')
    
    voucher = models.ForeignKey(Voucher, on_delete=models.SET_NULL, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=0, default=0, help_text="Số tiền đã được giảm")
    
    @property
    def final_price(self):
        return self.total_price - self.discount_amount
    
    def __str__(self):
        return f"Đơn hàng #{self.id} - {self.full_name}"

# --- MODEL ORDERITEM (Như cũ) ---
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=0)
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Đơn hàng #{self.order.id})"

# --- MODEL REVIEW (MỚI) ---
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)]) # 1 đến 5 sao
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Đảm bảo mỗi user chỉ review 1 sản phẩm 1 lần
        unique_together = ('product', 'user') 
        ordering = ['-created_at'] # Sắp xếp mới nhất lên đầu

    def __str__(self):
        return f"Review {self.rating} sao cho '{self.product.name}' bởi {self.user.username}"
# --- MODEL CART (GIỎ HÀNG DATABASE) ---
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Giỏ hàng của {self.user.username}"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.cart_items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"