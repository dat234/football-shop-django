from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django import forms

class VietnameseAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': "Tên đăng nhập hoặc mật khẩu không đúng.",
        'inactive': "Tài khoản này đã bị vô hiệu hóa.",
    }
    
    username = forms.CharField(
        label="Tên đăng nhập",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'required': 'Vui lòng nhập tên đăng nhập.'}
    )
    
    password = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        error_messages={'required': 'Vui lòng nhập mật khẩu.'}
    )


class VietnameseUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        error_messages={'required': 'Vui lòng nhập địa chỉ email.'}
    )
    
    username = forms.CharField(
        label="Tên đăng nhập",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={
            'required': 'Vui lòng nhập tên đăng nhập.',
            'unique': 'Tên đăng nhập này đã tồn tại.',
        },
        help_text='Tên đăng nhập chỉ có thể chứa chữ cái, số và các ký tự @/./+/-/_'
    )
    
    password1 = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        error_messages={'required': 'Vui lòng nhập mật khẩu.'},
        help_text='Mật khẩu phải có ít nhất 8 ký tự và không được quá đơn giản.'
    )
    
    password2 = forms.CharField(
        label="Xác nhận mật khẩu",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        error_messages={'required': 'Vui lòng xác nhận mật khẩu.'},
        help_text='Nhập lại mật khẩu để xác nhận.'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tùy chỉnh thông báo lỗi
        self.error_messages['password_mismatch'] = 'Hai mật khẩu không khớp.'
        self.error_messages['password_too_similar'] = 'Mật khẩu quá giống với thông tin cá nhân.'
        self.error_messages['password_too_short'] = 'Mật khẩu phải có ít nhất 8 ký tự.'
        self.error_messages['password_too_common'] = 'Mật khẩu quá phổ biến.'
        self.error_messages['password_entirely_numeric'] = 'Mật khẩu không thể chỉ chứa số.'
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Hai mật khẩu không khớp.")
        return password2
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email này đã được đăng ký.")
        return email