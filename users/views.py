# users/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache 
# Import thêm Cart, CartItem, Product để xử lý gộp giỏ hàng
from store.models import Order, OrderItem, Review, Cart, CartItem, Product 
from users.templates.users.forms import VietnameseAuthenticationForm, VietnameseUserCreationForm

# --- HÀM PHỤ TRỢ: Gộp giỏ hàng Session vào Database ---
def merge_cart_from_session(request, user):
    session_cart = request.session.get('cart', {})
    
    if session_cart:
        # Lấy hoặc tạo giỏ hàng DB cho user
        user_cart, created = Cart.objects.get_or_create(user=user)
        
        for product_id_str, quantity in session_cart.items():
            try:
                product = Product.objects.get(id=int(product_id_str))
                
                # Kiểm tra xem sản phẩm đã có trong giỏ DB chưa
                cart_item, created = CartItem.objects.get_or_create(cart=user_cart, product=product)
                
                if created:
                    cart_item.quantity = quantity
                else:
                    cart_item.quantity += quantity # Nếu có rồi thì cộng dồn
                
                # Kiểm tra không vượt quá tồn kho
                if cart_item.quantity > product.stock:
                    cart_item.quantity = product.stock
                
                cart_item.save()
            except Product.DoesNotExist:
                continue
            
        # Xóa giỏ hàng session sau khi đã chuyển xong
        request.session['cart'] = {}


# --- Views Đăng ký ---
def register_view(request):
    if request.method == 'POST':
        form = VietnameseUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Xóa sạch session cũ trước khi login mới
            request.session.flush()
            login(request, user)
            return redirect('home')
    else:
        form = VietnameseUserCreationForm()
    return render(request, 'users/register.html', {'form': form})

# --- Views Đăng nhập (Đã nâng cấp gộp giỏ hàng) ---
def login_view(request):
    if request.method == 'POST':
        form = VietnameseAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # 1. Lấy giỏ hàng tạm từ session TRƯỚC KHI flush
            temp_cart = request.session.get('cart', {})
            
            # 2. Xóa sạch session cũ (bảo mật)
            request.session.flush()
            
            # 3. Đăng nhập
            login(request, user)
            
            # 4. Khôi phục lại giỏ session vào session mới
            request.session['cart'] = temp_cart
            
            # 5. GỌI HÀM GỘP GIỎ HÀNG
            merge_cart_from_session(request, user)
            
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
    else:
        form = VietnameseAuthenticationForm()
    
    return render(request, 'users/login.html', {'form': form})

# --- Views Đăng xuất ---
@never_cache 
def logout_view(request):
    request.session.flush()
    logout(request)
    return redirect('home')

# --- View Lịch sử Đơn hàng ---
@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {'orders': orders}
    return render(request, 'users/order_history.html', context)

# --- View Chi tiết Đơn hàng ---
@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.all()

    item_review_status = {}
    if order.status == 'Hoàn thành':
        for item in order_items:
            has_reviewed = Review.objects.filter(
                product=item.product,
                user=request.user
            ).exists()
            item_review_status[item.id] = has_reviewed

    context = {
        'order': order,
        'order_items': order_items,
        'item_review_status': item_review_status
    }
    return render(request, 'users/order_detail.html', context)