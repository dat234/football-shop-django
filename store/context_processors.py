from .models import Cart

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
