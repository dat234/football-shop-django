from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

# --- CÁC LỰA CHỌN TRẠNG THÁI ---
ORDER_STATUS_CHOICES = [
    ('Mới', 'Mới'),
    ('Chờ thanh toán', 'Chờ thanh toán'),
    ('Đang xử lý', 'Đang xử lý'),
    ('Đang giao', 'Đang giao'),
    ('Hoàn thành', 'Hoàn thành'),
    ('Đã hủy', 'Đã hủy'),
]

PAYMENT_METHOD_CHOICES = [
    ('cod', 'Thanh toán khi nhận hàng (COD)'),
    ('qr', 'Chuyển khoản ngân hàng (QR)'),
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
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='cod')
    
    voucher = models.ForeignKey(Voucher, on_delete=models.SET_NULL, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=0, default=0, help_text="Số tiền đã được giảm")

    payment_proof = models.ImageField(upload_to='payment_proofs/', null=True, blank=True)
    
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

# --- MODEL CARTITEM (GIỎ HÀNG DATABASE) ---
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

# --- MODEL USERPROFILE ---
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True) # Dùng để pre-fill checkout
    is_email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

# --- MODEL NOTIFICATION (MỚI) ---
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Sử dụng get_or_create để đảm bảo profile luôn tồn tại
    UserProfile.objects.get_or_create(user=instance)
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()

# --- SIGNALS CHO THÔNG BÁO ĐƠN HÀNG ---

# 1. Bắt trạng thái cũ trước khi lưu để so sánh
@receiver(pre_save, sender=Order)
def track_order_status(sender, instance, **kwargs):
    try:
        old_instance = Order.objects.get(pk=instance.pk)
        instance._old_status = old_instance.status
    except Order.DoesNotExist:
        instance._old_status = None

# 2. Tạo thông báo sau khi lưu
@receiver(post_save, sender=Order)
def create_order_notification(sender, instance, created, **kwargs):
    if created:
        # Chỉ tạo thông báo thành công ngay nếu là COD
        if instance.payment_method == 'cod':
            Notification.objects.create(
                user=instance.user,
                title="Đặt hàng thành công",
                message=f"Đơn hàng #{instance.id} của bạn đã được đặt thành công. Chúng tôi sẽ sớm liên hệ."
            )
    elif instance._old_status is not None and instance._old_status != instance.status:
        # Nếu là QR và vừa chuyển từ Chờ thanh toán -> Đang xử lý (đã upload ảnh)
        if instance.payment_method == 'qr' and instance._old_status == 'Chờ thanh toán' and instance.status != 'Chờ thanh toán':
             Notification.objects.create(
                user=instance.user,
                title="Đặt hàng thành công",
                message=f"Chúng tôi đã nhận được thông tin thanh toán cho đơn hàng #{instance.id}. Đơn hàng đang được xử lý."
            )
        else:
            # Thông báo khi trạng thái thay đổi thông thường
            Notification.objects.create(
                user=instance.user,
                title="Cập nhật đơn hàng",
                message=f"Đơn hàng #{instance.id} của bạn đã chuyển sang trạng thái: {instance.status}."
            )