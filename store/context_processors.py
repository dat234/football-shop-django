from .models import Cart, Notification

def cart_count(request):
    """
    Context processor to add cart item count to every template context
    """
    cart_items_count = 0
    
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_items_count = cart.cart_items.count()
        except Cart.DoesNotExist:
            cart_items_count = 0
    
    return {'cart_count': cart_items_count}

def notifications(request):
    if request.user.is_authenticated:
        # Lấy tất cả thông báo, sắp xếp mới nhất
        user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        # Đếm số lượng chưa đọc
        unread_count = user_notifications.filter(is_read=False).count()
        return {
            'notifications': user_notifications,
            'notification_unread_count': unread_count
        }
    return {
        'notifications': [],
        'notification_unread_count': 0
    }