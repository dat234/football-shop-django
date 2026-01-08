# Imports từ Django
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg # Import Avg để tính trung bình
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
import random
import string


from .models import Product, Category, Order, OrderItem, Voucher, Review, Cart, CartItem, UserProfile

# Hàm hỗ trợ sinh mã đơn hàng ngẫu nhiên (VD: 839201)
def generate_order_code():
    # Tạo chuỗi 6 số ngẫu nhiên.
    return 'DH' + ''.join(random.choices(string.digits, k=6))

# -----------------------------------------------------------------------------
# GĐ 19: Home (Tìm kiếm, Lọc, Sắp xếp, Phân trang)
# -----------------------------------------------------------------------------
def home(request):
    all_categories = Category.objects.all()
    search_query = request.GET.get('q')
    category_id = request.GET.get('category')
    sort_by = request.GET.get('sort', '-id') # Mặc định mới nhất

    products = Product.objects.all().order_by('-id') # Bắt đầu với tất cả, sắp xếp mặc định

    # Lọc theo tìm kiếm
    if search_query:
        # Chỉ tìm kiếm trong tên sản phẩm
        products = products.filter(name__icontains=search_query)

    # Lọc theo danh mục
    if category_id:
        products = products.filter(category__id=category_id)

    # Sắp xếp (Chỉ sắp xếp nếu products là QuerySet, nếu là list thì sort bằng python)
    if not isinstance(products, list):
        if sort_by in ['price_asc', 'price_desc', '-id']:
            if sort_by == 'price_asc':
                products = products.order_by('price')
            elif sort_by == 'price_desc':
                products = products.order_by('-price')
            # else: đã order_by('-id') ở trên rồi


    # Phân trang
    query_params = request.GET.copy()
    if 'page' in query_params: del query_params['page']
    query_string = query_params.urlencode()

    paginator = Paginator(products, 12) # 12 sản phẩm/trang
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'all_categories': all_categories,
        'search_query': search_query,
        'current_category_id': int(category_id) if category_id else None,
        'query_string': query_string,
        'current_sort': sort_by
    }
    return render(request, 'store/home.html', context)

# -----------------------------------------------------------------------------
# GĐ 21 (Sửa đổi logic GET và POST): Trang Chi tiết Sản phẩm
# -----------------------------------------------------------------------------
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.all()
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg']

    # ----- LOGIC KIỂM TRA ĐIỀU KIỆN REVIEW -----
    can_review = False 
    has_reviewed = False
    review_message = "" 

    if request.user.is_authenticated:
        # 1. Kiểm tra xem đã review chưa
        has_reviewed = Review.objects.filter(product=product, user=request.user).exists()
        if has_reviewed:
            review_message = "Bạn đã đánh giá sản phẩm này rồi."
        else:
            # 2. Nếu chưa review, kiểm tra xem đã mua và hoàn thành chưa
            has_completed_order = Order.objects.filter(
                user=request.user,
                status='Hoàn thành',
                items__product=product
            ).exists()
            if has_completed_order:
                can_review = True 
            else:
                review_message = "Bạn cần mua và nhận hàng thành công trước khi đánh giá."
    else:
        review_message = "Đăng nhập để đánh giá."

    # Xử lý POST để gửi review
    if request.method == 'POST' and request.POST.get('action') == 'submit_review':
        if not request.user.is_authenticated:
             return redirect('login')
        if has_reviewed:
             messages.error(request, "Bạn đã đánh giá sản phẩm này rồi.")
             return redirect('product_detail', product_id=product_id)

        # Kiểm tra lại lần cuối (an toàn)
        can_actually_review = Order.objects.filter(
            user=request.user, status='Hoàn thành', items__product=product
        ).exists()
        if not can_actually_review:
            messages.error(request, "Bạn cần mua và nhận hàng thành công trước khi đánh giá.")
            return redirect('product_detail', product_id=product_id)

        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        if not rating or not rating.isdigit() or int(rating) not in range(1, 6):
            messages.error(request, "Vui lòng chọn số sao hợp lệ.")
            return redirect('product_detail', product_id=product_id)

        Review.objects.create(
            product=product, user=request.user, rating=int(rating), comment=comment
        )
        messages.success(request, "Cảm ơn bạn đã gửi đánh giá!")
        return redirect('product_detail', product_id=product_id)

    context = {
        'product': product,
        'reviews': reviews,
        'average_rating': average_rating,
        'can_review': can_review, 
        'has_reviewed': has_reviewed, 
        'review_message': review_message, 
    }
    return render(request, 'store/product_detail.html', context)

# -----------------------------------------------------------------------------
# GĐ 26: Thêm vào Giỏ hàng (Hỗ trợ DB Cart)
# -----------------------------------------------------------------------------
@login_required(login_url='login')
def add_to_cart(request, product_id):
    if request.method == 'POST' and request.POST.get('action') == 'add_to_cart':
        quantity = int(request.POST.get('quantity', 1))
        product = get_object_or_404(Product, id=product_id)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        
        if created:
            new_quantity = quantity
        else:
            new_quantity = cart_item.quantity + quantity
        
        message_text = ""
        status = "success"

        if new_quantity <= product.stock:
            cart_item.quantity = new_quantity
            cart_item.save()
            message_text = f"Đã thêm {quantity} '{product.name}' vào giỏ."
        else:
            # Tính số lượng tối đa có thể thêm
            available_to_add = product.stock - cart_item.quantity
            if available_to_add > 0:
                cart_item.quantity = product.stock
                cart_item.save()
                message_text = f"Chỉ còn {product.stock} sản phẩm. Đã thêm tối đa vào giỏ."
                status = "warning"
            else:
                message_text = f"Sản phẩm '{product.name}' đã đạt giới hạn tồn kho trong giỏ."
                status = "error"
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Tính tổng số lượng item trong giỏ để update badge trên header (nếu cần)
            total_items = sum(item.quantity for item in cart.cart_items.all())
            
            return JsonResponse({
                'status': status,
                'message': message_text,
                'cart_count': total_items # Trả về số lượng mới để JS cập nhật header
            })

        # --- NẾU KHÔNG PHẢI AJAX (Fallback) ---
        if status == 'success':
            messages.success(request, message_text)
        elif status == 'warning':
            messages.warning(request, message_text)
        else:
            messages.error(request, message_text)

    return redirect('product_detail', product_id=product_id)


# -----------------------------------------------------------------------------
# GĐ 26: Xem Giỏ hàng (Hỗ trợ DB Cart)
# -----------------------------------------------------------------------------
def cart_view(request):
    detailed_cart_items = []
    total_price = 0

    if request.user.is_authenticated:
        # --- Dùng Database ---
        cart, _ = Cart.objects.get_or_create(user=request.user)
        db_items = cart.cart_items.all()
        for item in db_items:
            # Kiểm tra tồn kho thực tế
            if item.quantity > item.product.stock:
                item.quantity = item.product.stock
                item.save()
                messages.warning(request, f"Số lượng '{item.product.name}' đã được cập nhật do thay đổi tồn kho.")
            
            if item.quantity > 0:
                detailed_cart_items.append({
                    'product': item.product,
                    'quantity': item.quantity,
                    'subtotal': item.subtotal
                })
                total_price += item.subtotal
            else:
                item.delete()
    else:
        # --- Dùng Session ---
        cart = request.session.get('cart', {})
        for product_id, quantity in list(cart.items()):
            try:
                product = Product.objects.get(id=int(product_id))
                if quantity > product.stock:
                    cart[product_id] = product.stock
                    quantity = product.stock
                    messages.warning(request, f"Số lượng '{product.name}' đã được cập nhật do thay đổi tồn kho.")

                if quantity > 0:
                    subtotal = product.price * quantity
                    detailed_cart_items.append({
                        'product': product,
                        'quantity': quantity,
                        'subtotal': subtotal,
                    })
                    total_price += subtotal
                else:
                    del cart[product_id]
            except Product.DoesNotExist:
                del cart[product_id]
        
        request.session['cart'] = cart # Lưu lại session cart nếu có thay đổi

    context = {
        'cart_items': detailed_cart_items,
        'total_price': total_price,
    }
    return render(request, 'store/cart.html', context)


# -----------------------------------------------------------------------------
# GĐ 26: Cập nhật Giỏ hàng (Hỗ trợ DB Cart)
# -----------------------------------------------------------------------------
def update_cart(request, product_id):
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity'))
        except (ValueError, TypeError):
            quantity = 1

        product = get_object_or_404(Product, id=product_id)
        msg = ""
        status = "success"

        if request.user.is_authenticated:
            # --- Dùng Database ---
            cart, _ = Cart.objects.get_or_create(user=request.user)
            if quantity > 0:
                if quantity <= product.stock:
                    cart_item, _ = CartItem.objects.get_or_create(cart=cart, product=product)
                    cart_item.quantity = quantity
                    cart_item.save()
                    msg = "Đã cập nhật số lượng."
                else:
                    msg = "Số lượng vượt quá tồn kho."
                    status = "error"
            else:
                # Xóa
                CartItem.objects.filter(cart=cart, product=product).delete()
                msg = "Đã xóa sản phẩm khỏi giỏ hàng."
        else:
            # --- Dùng Session ---
            cart = request.session.get('cart', {})
            msg = "Đã cập nhật (Session)."
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': status,
                'message': msg,
                # Nếu bạn muốn trang giỏ hàng tự reload để cập nhật giá tiền:
                'redirect_url': request.META.get('HTTP_REFERER', '/') 
                # Hoặc nếu bạn muốn JS tự sửa số tiền thì phải trả về total_price ở đây
            })

        # --- Fallback ---
        if status == 'success': messages.success(request, msg)
        else: messages.error(request, msg)

    return redirect('cart_view')


# -----------------------------------------------------------------------------
# GĐ 26: Checkout (Hỗ trợ DB Cart)
# -----------------------------------------------------------------------------
def checkout(request):
    detailed_cart_items = []
    total_price = 0
    
    # --- Lấy giỏ hàng (DB hoặc Session) ---
    if request.user.is_authenticated:
        cart_db, _ = Cart.objects.get_or_create(user=request.user)
        db_items = cart_db.cart_items.all()
        if not db_items:
             return redirect('home')
        for item in db_items:
             # Kiểm tra tồn kho
             if item.quantity > item.product.stock:
                 item.quantity = item.product.stock
                 item.save()
             detailed_cart_items.append({'product': item.product, 'quantity': item.quantity, 'subtotal': item.subtotal})
             total_price += item.subtotal
    else:
        cart_session = request.session.get('cart', {})
        if not cart_session:
            return redirect('home')
        
        for product_id, quantity in list(cart_session.items()):
            try:
                product = Product.objects.get(id=int(product_id))
                if quantity > product.stock:
                    cart_session[product_id] = product.stock
                    quantity = product.stock
                subtotal = product.price * quantity
                detailed_cart_items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})
                total_price += subtotal
            except Product.DoesNotExist:
                del cart_session[product_id]
        request.session['cart'] = cart_session

    # 1. Chuẩn bị dữ liệu mặc định (Pre-fill)
    initial_data = {
        'full_name': '',
        'email': '',
        'phone': '',
        'address': ''
    }
    if request.user.is_authenticated:
        initial_data['email'] = request.user.email
        initial_data['full_name'] = request.user.get_full_name()
        if hasattr(request.user, 'userprofile'):
            initial_data['phone'] = request.user.userprofile.phone_number or ''
            initial_data['address'] = request.user.userprofile.address or ''

    # 2. Ưu tiên dữ liệu từ session (nếu user vừa nhập sai hoặc reload), nếu không dùng initial_data
    form_data = request.session.get('checkout_form_data', initial_data)

    # --- Xử lý Voucher ---
    voucher_code = request.session.get('voucher_code')
    voucher = None
    discount_amount = 0
    if voucher_code:
        try:
            voucher = Voucher.objects.get(code__iexact=voucher_code)
            is_valid, message = voucher.is_valid(total_price)
            if is_valid:
                discount_amount = voucher.discount_amount
            else:
                messages.error(request, message)
                del request.session['voucher_code']
                voucher = None
        except Voucher.DoesNotExist:
            del request.session['voucher_code']

    final_price = total_price - discount_amount

    # --- XỬ LÝ POST ---
    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        action = request.POST.get('action')

        form_data = {
            'full_name': request.POST.get('full_name', ''),
            'email': request.POST.get('email', ''),
            'phone': request.POST.get('phone', ''),
            'address': request.POST.get('address', ''),
        }
        request.session['checkout_form_data'] = form_data

        if action == 'apply_voucher':
            code_from_form = request.POST.get('voucher_code_input')
            if not code_from_form: 
                msg = "Vui lòng nhập mã giảm giá."
                if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                messages.error(request, msg); return redirect('checkout')
            try:
                voucher_to_apply = Voucher.objects.get(code__iexact=code_from_form)
                is_valid, message = voucher_to_apply.is_valid(total_price)
                if is_valid:
                    request.session['voucher_code'] = voucher_to_apply.code
                    msg = f"Đã áp dụng mã '{voucher_to_apply.code}'."
                    if is_ajax: 
                        return JsonResponse({'status': 'success', 'message': msg, 'redirect_url': ''}) # reload để cập nhật giá
                    messages.success(request, msg)
                else:
                    if is_ajax: return JsonResponse({'status': 'error', 'message': message})
                    messages.error(request, message)
            except Voucher.DoesNotExist: 
                msg = "Mã giảm giá không tồn tại."
                if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                messages.error(request, msg)
            return redirect('checkout')

        elif action == 'remove_voucher':
            if 'voucher_code' in request.session: del request.session['voucher_code']
            msg = "Đã xóa mã giảm giá."
            if is_ajax: return JsonResponse({'status': 'success', 'message': msg, 'redirect_url': ''})
            messages.success(request, msg)
            return redirect('checkout')

        elif action == 'place_order':
            full_name = form_data['full_name']
            email = form_data['email']
            phone = form_data['phone']
            address = form_data['address']

            if not all([full_name, email, phone, address]):
                msg = "Vui lòng điền đầy đủ thông tin giao hàng."
                if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                messages.error(request, msg); return redirect('checkout')

            payment_method = request.POST.get('payment_method', 'cod')

            # Sinh mã đơn hàng ngay tại đây để dùng chung cho cả Session (QR) và DB (COD)
            new_order_code = generate_order_code()

            # --- LOGIC MỚI: TÁCH LUỒNG COD VÀ QR ---
            if payment_method == 'qr':
                # 1. Kiểm tra tồn kho trước (nhưng chưa trừ)
                for item_data in detailed_cart_items:
                    if item_data['product'].stock < item_data['quantity']:
                        msg = f"Sản phẩm '{item_data['product'].name}' không đủ số lượng."
                        if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                        messages.error(request, msg); return redirect('cart_view')
                
                
                # Lưu ý: Decimal không lưu được vào session JSON, cần chuyển sang float/str
                request.session['pending_order'] = {
                    'full_name': full_name,
                    'email': email,
                    'phone': phone,
                    'address': address,
                    'total_price': float(total_price),
                    'discount_amount': float(discount_amount),
                    'voucher_code': voucher.code if voucher else None,
                    'payment_method': 'qr',
                    'order_code': new_order_code  # Lưu mã đơn hàng vào session
                }
                
                msg = "Vui lòng thực hiện thanh toán."
                success_url = reverse('payment_info', kwargs={'order_code': new_order_code})
                
                if is_ajax:
                    return JsonResponse({'status': 'success', 'message': msg, 'redirect_url': success_url})
                return redirect(success_url)

            else: 
                # --- LOGIC CŨ CHO COD (Tạo đơn ngay) ---
                order_data = {
                    'full_name': full_name, 'email': email, 'phone': phone, 'address': address,
                    'total_price': total_price, 'discount_amount': discount_amount, 'voucher': voucher,
                    'payment_method': 'cod',
                    'order_code': new_order_code, # Lưu mã vào DB
                    'status': 'Mới',
                }
                if request.user.is_authenticated: order_data['user'] = request.user

                try:
                    new_order = Order.objects.create(**order_data)

                    for item_data in detailed_cart_items:
                        product = item_data['product']
                        quantity = item_data['quantity']
                        product.refresh_from_db() # Lấy tồn kho mới nhất
                        if product.stock < quantity:
                            new_order.delete() # Rollback
                            msg = f"Sản phẩm '{product.name}' vừa hết hàng."
                            if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                            messages.error(request, msg); return redirect('cart_view')
                        
                        OrderItem.objects.create(
                            order=new_order, product=product, quantity=quantity, price_at_purchase=product.price
                        )
                        product.stock -= quantity
                        product.save()

                    # Xóa giỏ hàng và session
                    if request.user.is_authenticated:
                        Cart.objects.filter(user=request.user).delete()
                    else:
                        del request.session['cart']
                    
                    if 'voucher_code' in request.session: del request.session['voucher_code']
                    if 'checkout_form_data' in request.session: del request.session['checkout_form_data']

                    msg = "Đặt hàng thành công!"
                    success_url = reverse('order_success')

                    if is_ajax:
                        return JsonResponse({'status': 'success', 'message': msg, 'redirect_url': success_url})
                    return redirect(success_url)

                except Exception as e:
                    if 'new_order' in locals(): new_order.delete()
                    msg = f"Đã xảy ra lỗi: {str(e)}"
                    if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                    messages.error(request, msg)
                    return redirect('checkout')

    context = {
        'cart_items': detailed_cart_items,
        'total_price': total_price,
        'voucher': voucher,
        'discount_amount': discount_amount,
        'final_price': final_price,
        'form_data': form_data,
    }
    return render(request, 'store/checkout.html', context)

# -----------------------------------------------------------------------------
# GĐ 27: Thông tin Chuyển khoản
# -----------------------------------------------------------------------------
def payment_info(request, order_code):
    # 1. Lấy thông tin từ Session
    pending_order = request.session.get('pending_order')
    if not pending_order:
        messages.error(request, "Không tìm thấy thông tin đơn hàng chờ thanh toán.")
        return redirect('home')
    
    # Kiểm tra mã đơn hàng trên URL có khớp với session không
    if pending_order.get('order_code') != order_code:
        messages.error(request, "Thông tin đơn hàng không hợp lệ.")
        return redirect('home')
    
    # Giả lập object order để hiển thị trên template (vì template đang dùng order.total_price)
    # Dùng class type dynamic hoặc dict
    class TempOrder:
        def __init__(self, data):
            self.total_price = data['total_price']
            self.discount_amount = data['discount_amount']
            self.final_price = self.total_price - self.discount_amount
            self.full_name = data['full_name']
            self.order_code = data.get('order_code') # Lấy mã từ session để hiển thị
            self.items = [] # Khởi tạo danh sách items
    
    display_order = TempOrder(pending_order)
    
    # Lấy danh sách sản phẩm để hiển thị
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        display_order.items = cart.cart_items.all()
    else:
        cart_session = request.session.get('cart', {})
        items_list = []
        for p_id, qty in cart_session.items():
            try:
                product = Product.objects.get(id=int(p_id))
                items_list.append({'product': product, 'quantity': qty})
            except Product.DoesNotExist:
                pass
        display_order.items = items_list

    if request.method == 'POST':
        if 'payment_proof' in request.FILES:
            proof_image = request.FILES['payment_proof']
            
            # --- BẮT ĐẦU TẠO ĐƠN HÀNG THỰC TẾ ---
            try:
                # 1. Lấy lại Voucher nếu có
                voucher = None
                if pending_order['voucher_code']:
                    try:
                        voucher = Voucher.objects.get(code=pending_order['voucher_code'])
                    except Voucher.DoesNotExist:
                        pass

                # 2. Tạo Order
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    full_name=pending_order['full_name'],
                    email=pending_order['email'],
                    phone=pending_order['phone'],
                    address=pending_order['address'],
                    total_price=pending_order['total_price'],
                    discount_amount=pending_order['discount_amount'],
                    voucher=voucher,
                    payment_method='qr',
                    order_code=pending_order['order_code'], # Lưu mã từ session vào DB
                    status='Mới', # Hoặc 'Đang xử lý' tùy bạn
                    payment_proof=proof_image,
                    note=f"Mã thanh toán: {pending_order.get('order_code')}" 
                )

                # 3. Tạo OrderItem và Trừ tồn kho 
                if request.user.is_authenticated:
                    cart = Cart.objects.get(user=request.user)
                    cart_items = cart.cart_items.all()
                    
                    for item in cart_items:
                        # Kiểm tra tồn kho lần cuối
                        if item.product.stock < item.quantity:
                            order.delete() # Rollback
                            messages.error(request, f"Sản phẩm {item.product.name} vừa hết hàng.")
                            return redirect('cart_view')

                        OrderItem.objects.create(
                            order=order, product=item.product, quantity=item.quantity, price_at_purchase=item.product.price
                        )
                        item.product.stock -= item.quantity
                        item.product.save()
                    
                    # Xóa Cart DB
                    cart.cart_items.all().delete()
                
                else:
                    # Xử lý cho Session Cart (Guest)
                    cart_session = request.session.get('cart', {})
                    for p_id, qty in cart_session.items():
                        product = Product.objects.get(id=int(p_id))
                        if product.stock < qty:
                            order.delete()
                            messages.error(request, f"Sản phẩm {product.name} vừa hết hàng.")
                            return redirect('cart_view')
                            
                        OrderItem.objects.create(
                            order=order, product=product, quantity=qty, price_at_purchase=product.price
                        )
                        product.stock -= qty
                        product.save()
                    
                    del request.session['cart']

                # 4. Dọn dẹp session
                del request.session['pending_order']
                if 'voucher_code' in request.session: del request.session['voucher_code']
                if 'checkout_form_data' in request.session: del request.session['checkout_form_data']

                return redirect('order_success')

            except Exception as e:
                messages.error(request, f"Lỗi khi tạo đơn hàng: {str(e)}")
                return redirect('cart_view')

        else:
            messages.error(request, "Vui lòng tải lên ảnh bằng chứng chuyển khoản.")
    
    return render(request, 'store/payment_info.html', {'order': display_order})

# -----------------------------------------------------------------------------
# GĐ 10: Trang Cảm ơn
# -----------------------------------------------------------------------------
def order_success(request):
    return render(request, 'store/order_success.html')

# -----------------------------------------------------------------------------
# GĐ 0: Trang Giới thiệu
# -----------------------------------------------------------------------------
def landing_page(request):
    featured_products = Product.objects.all().order_by('?')[:5]
    context = {
        'featured_products': featured_products
    }
    return render(request, 'store/landing_page.html', context)