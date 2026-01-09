from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache 
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.models import User

from django.contrib import messages
from django.shortcuts import redirect
from allauth.account.models import EmailAddress
# Import thêm Cart, CartItem, Product để xử lý gộp giỏ hàng
from store.models import Order, OrderItem, Review, Cart, CartItem, Product, UserProfile, Notification
from users.templates.users.forms import VietnameseAuthenticationForm, VietnameseUserCreationForm
from django.http import JsonResponse

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
            # Thiết lập backend thủ công vì project dùng nhiều backend (ModelBackend + Allauth)
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            
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
    return redirect('landing_page')

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

@login_required
def profile_view(request):
    user = request.user
    # Đảm bảo profile tồn tại
    if not hasattr(user, 'userprofile'):
        UserProfile.objects.create(user=user)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            full_name = request.POST.get('full_name')
            phone = request.POST.get('phone')
            avatar = request.FILES.get('avatar')

            if full_name:
                names = full_name.strip().split(' ', 1)
                user.first_name = names[0]
                user.last_name = names[1] if len(names) > 1 else ''
                user.save()

            if phone:
                user.userprofile.phone_number = phone
            
            if avatar:
                user.userprofile.avatar = avatar
            
            user.userprofile.save()
            messages.success(request, 'Cập nhật hồ sơ thành công!')
            
        elif action == 'verify_email':
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            verify_link = request.build_absolute_uri(f'/verify-email/{uid}/{token}/')
            
            subject = 'Xác minh email BODAH Shop'
            message = f'Chào {user.username},\n\nVui lòng nhấp vào link sau để xác minh email của bạn:\n{verify_link}'
            from_email = settings.EMAIL_HOST_USER
            
            try:
                send_mail(subject, message, from_email, [user.email])
                messages.info(request, f'Đã gửi email xác minh tới {user.email}. Vui lòng kiểm tra hộp thư.')
            except Exception as e:
                messages.error(request, 'Lỗi gửi mail. Vui lòng thử lại sau.')

        return redirect('profile')

    # Đã sửa đường dẫn template thành 'users/profile.html'
    return render(request, 'users/profile.html')

def verify_email_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.userprofile.is_email_verified = True
        user.userprofile.save()
        
        # Tạo thông báo xác minh thành công
        Notification.objects.create(
            user=user,
            title="Xác minh tài khoản",
            message="Chúc mừng! Email của bạn đã được xác minh thành công."
        )
        
        messages.success(request, 'Xác minh email thành công!')
        return redirect('profile')
    else:
        messages.error(request, 'Link xác minh không hợp lệ hoặc đã hết hạn.')
        return redirect('home')

# --- API: Lấy chi tiết thông báo và đánh dấu đã đọc ---
@login_required
def get_notification_detail(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    
    # Đánh dấu là đã đọc
    if not notification.is_read:
        notification.is_read = True
        notification.save()
    
    return JsonResponse({
        'title': notification.title,
        'message': notification.message,
        'created_at': notification.created_at.strftime('%H:%M %d/%m/%Y')
    })

def send_verification_email(request):
    if request.user.is_authenticated:
        # Lấy bản ghi EmailAddress của user hiện tại
        email_obj = EmailAddress.objects.filter(user=request.user, email=request.user.email).first()
        
        if email_obj:
            if email_obj.verified:
                messages.info(request, "Email của bạn đã được xác minh.")
            else:
                # Gửi mail xác nhận bằng hàm chuẩn của phiên bản mới
                email_obj.send_confirmation(request)
                messages.success(request, "Một email xác nhận đã được gửi tới hộp thư của bạn!")
        else:
            # Trường hợp user chưa có bản ghi EmailAddress (hiếm gặp)
            email_obj = EmailAddress.objects.create(
                user=request.user, 
                email=request.user.email, 
                primary=True, 
                verified=False
            )
            email_obj.send_confirmation(request)
            messages.success(request, "Đã khởi tạo thông tin và gửi email xác nhận!")
            
    return redirect('profile')