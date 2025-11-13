import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime

from utils import paginate
from uploads import save_upload
from auth import roles_required
from passwords import generate_reset_token, verify_reset_token

from models import (
    db, User, Profile, Role, Category,
    ForumThread, ForumPost, BlogPost, BlogComment,
    Consultant, Product, Order, OrderItem,
    Inventory, Cart, CartItem
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agrifarma.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Jinja filters
def _timesince(dt, default="just now"):
    if not dt:
        return default
    now = datetime.utcnow()
    if isinstance(dt, datetime):
        diff = now - dt
    else:
        return default
    periods = [
        (diff.days // 365, "year", "years"),
        (diff.days // 30, "month", "months"),
        (diff.days // 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds // 3600, "hour", "hours"),
        (diff.seconds // 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    ]
    for period, singular, plural in periods:
        if period:
            return f"{period} {singular if period == 1 else plural} ago"
    return default

def _format_date(dt, fmt="%Y-%m-%d"):
    if not dt:
        return ""
    try:
        return dt.strftime(fmt)
    except Exception:
        return str(dt)

app.jinja_env.filters["timesince"] = _timesince
app.jinja_env.filters["date"] = _format_date

# init
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))

with app.app_context():
    upload_root = app.config['UPLOAD_FOLDER']
    if os.path.exists(upload_root) and not os.path.isdir(upload_root):
        os.replace(upload_root, upload_root + ".bak")
    os.makedirs(upload_root, exist_ok=True)
    for sub in ('profile_pics', 'blog_media', 'products'):
        path = os.path.join(upload_root, sub)
        if os.path.exists(path) and not os.path.isdir(path):
            os.replace(path, path + ".bak")
        os.makedirs(path, exist_ok=True)

# ---------------- Core ----------------
@app.route('/')
def index():
    latest_threads = ForumThread.query.order_by(ForumThread.created_at.desc()).limit(6).all()
    latest_blogs = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(6).all()
    featured_products = Product.query.order_by(Product.rating.desc()).limit(8).all()
    stats = {
        'users': User.query.count(),
        'discussions': ForumThread.query.count(),
        'articles': BlogPost.query.count(),
        'products': Product.query.count()
    }
    return render_template('index.html',
                           latest_threads=latest_threads,
                           latest_blogs=latest_blogs,
                           featured_products=featured_products,
                           stats=stats)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        flash('Thanks for contacting us!', 'success')
        return redirect(url_for('index'))
    return render_template('contact.html')

# ---------------- Auth ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name'); email = request.form.get('email'); password = request.form.get('password')
        if not User.query.filter_by(email=email).first():
            u = User(name=name, email=email); u.set_password(password)
            db.session.add(u); db.session.flush()
            db.session.add(Profile(user_id=u.id,
                                   city=request.form.get('city'),
                                   state=request.form.get('state'),
                                   country=request.form.get('country'),
                                   profession=request.form.get('profession'),
                                   expertise=request.form.get('expertise')))
            role = Role.query.filter_by(name='user').first() or Role(name='user')
            db.session.add(role); u.roles.append(role)
            db.session.commit(); flash('Registration successful. Please login.', 'success')
            return redirect(url_for('login'))
        flash('Email already registered.', 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email'); password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user); flash('Welcome back!', 'success'); return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user(); flash('Logged out.', 'info'); return redirect(url_for('index'))

@app.route('/profile/<int:user_id>')
def profile(user_id):
    u = User.query.get_or_404(user_id)
    latest_threads = ForumThread.query.filter_by(user_id=u.id).order_by(ForumThread.created_at.desc()).limit(5).all()
    latest_blogs = BlogPost.query.filter_by(user_id=u.id).order_by(BlogPost.created_at.desc()).limit(5).all()
    recent_orders = []; orders_count = 0
    if current_user.is_authenticated and current_user.id == u.id:
        recent_orders = Order.query.filter_by(user_id=u.id).order_by(Order.created_at.desc()).limit(5).all()
        orders_count = Order.query.filter_by(user_id=u.id).count()
    return render_template('profile.html',
                           user=u,
                           latest_threads=latest_threads,
                           latest_blogs=latest_blogs,
                           recent_orders=recent_orders,
                           orders_count=orders_count)

@app.route('/edit-profile', methods=['GET','POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        flash('Profile updated', 'success'); return redirect(url_for('profile', user_id=current_user.id))
    return render_template('edit_profile.html')

# ---------------- Forum ----------------
@app.route('/forum')
def forum_home():
    categories = Category.query.filter_by(module='forum').all()
    latest_posts = ForumPost.query.order_by(ForumPost.created_at.desc()).limit(8).all()
    stats = {
        'total_threads': ForumThread.query.count(),
        'total_posts': ForumPost.query.count(),
        'active_users': User.query.count(),
        'newest_member': (User.query.order_by(User.join_date.desc()).first().name
                          if User.query.first() else 'N/A')
    }
    return render_template('forum_home.html', categories=categories, latest_posts=latest_posts, stats=stats)

@app.route('/forum/category/<int:category_id>')
def forum_category(category_id):
    category = Category.query.get_or_404(category_id)
    threads = ForumThread.query.filter_by(category_id=category.id).order_by(ForumThread.created_at.desc()).all()
    return render_template('forum_category.html', category=category, threads=threads)

@app.route('/forum/thread/<int:thread_id>', methods=['GET','POST'])
def forum_thread(thread_id):
    thread = ForumThread.query.get_or_404(thread_id)
    if request.method == 'POST' and current_user.is_authenticated:
        content = request.form.get('content')
        if content:
            db.session.add(ForumPost(thread_id=thread.id, user_id=current_user.id, content=content))
            db.session.commit(); flash('Reply posted!', 'success')
            return redirect(url_for('forum_thread', thread_id=thread.id))
    posts = ForumPost.query.filter_by(thread_id=thread.id).order_by(ForumPost.created_at.asc()).all()
    return render_template('forum_thread.html', thread=thread, posts=posts)

@app.route('/forum/create-thread/<int:category_id>', methods=['GET','POST'])
@login_required
def create_thread(category_id):
    category = Category.query.get_or_404(category_id)
    if request.method == 'POST':
        title = request.form.get('title'); content = request.form.get('content')
        if title and content:
            db.session.add(ForumThread(category_id=category.id, user_id=current_user.id, title=title, content=content))
            db.session.commit(); flash('Thread created!', 'success')
            return redirect(url_for('forum_category', category_id=category.id))
    return render_template('create_thread.html', category=category)

@app.route('/forum/search')
def forum_search():
    q = request.args.get('q',''); results = ForumThread.query.filter(ForumThread.title.ilike(f"%{q}%")).all() if q else []
    return render_template('forum_search.html', query=q, results=results)

# ---------------- Knowledge ----------------
@app.route('/knowledge')
def knowledge_home():
    categories = Category.query.filter_by(module='knowledge').all()
    featured_articles = BlogPost.query.order_by(BlogPost.views.desc()).limit(3).all()
    latest_articles = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(6).all()
    return render_template('knowledge_home.html',
                           categories=categories,
                           featured_articles=featured_articles,
                           latest_articles=latest_articles,
                           popular_tags=[], top_contributors=[])

@app.route('/knowledge/category/<int:category_id>')
def knowledge_category(category_id):
    category = Category.query.get_or_404(category_id)
    posts = BlogPost.query.filter_by(category_id=category.id).order_by(BlogPost.created_at.desc()).all()
    return render_template('knowledge_category.html', category=category, posts=posts)

@app.route('/knowledge/blog/<int:blog_id>', methods=['GET','POST'])
def blog_detail(blog_id):
    post = BlogPost.query.get_or_404(blog_id)
    if request.method == 'POST' and current_user.is_authenticated:
        content = request.form.get('content')
        if content:
            db.session.add(BlogComment(post_id=post.id, user_id=current_user.id, content=content))
            db.session.commit(); flash('Comment added!', 'success')
            return redirect(url_for('blog_detail', blog_id=post.id))
    comments = BlogComment.query.filter_by(post_id=post.id).order_by(BlogComment.created_at.asc()).all()
    related = BlogPost.query.filter(BlogPost.category_id==post.category_id, BlogPost.id!=post.id).limit(5).all()
    return render_template('blog_detail.html', post=post, comments=comments, related=related)

@app.route('/knowledge/create-blog', methods=['GET','POST'])
@login_required
def create_blog():
    categories = Category.query.filter_by(module='knowledge').all()
    if request.method == 'POST':
        title = request.form.get('title'); content = request.form.get('content'); category_id = request.form.get('category', type=int); tags = request.form.get('tags','')
        if title and content and category_id:
            db.session.add(BlogPost(category_id=category_id, user_id=current_user.id, title=title, content=content, tags=tags))
            db.session.commit(); flash('Blog published!', 'success')
            return redirect(url_for('knowledge_category', category_id=category_id))
    return render_template('create_blog.html', categories=categories)

@app.route('/knowledge/edit-blog/<int:blog_id>', methods=['GET','POST'])
@login_required
def edit_blog(blog_id):
    post = BlogPost.query.get_or_404(blog_id)
    if request.method == 'POST':
        post.title = request.form.get('title'); post.content = request.form.get('content'); post.tags = request.form.get('tags'); db.session.commit(); flash('Blog updated!', 'success')
        return redirect(url_for('blog_detail', blog_id=post.id))
    return render_template('edit_blog.html', post=post)

@app.route('/knowledge/search')
def knowledge_search():
    q = request.args.get('q','')
    results = BlogPost.query.filter((BlogPost.title.ilike(f"%{q}%")) | (BlogPost.tags.ilike(f"%{q}%"))).all() if q else []
    return render_template('knowledge_search.html', query=q, results=results)

# ---------------- Consultancy ----------------
@app.route('/consultancy')
def consultancy_home():
    categories = Category.query.filter_by(module='consultancy').all()
    return render_template('consultancy_home.html', categories=categories)

@app.route('/consultancy/consultant/<int:consultant_id>')
def consultant_profile(consultant_id):
    consultant = Consultant.query.get_or_404(consultant_id)
    return render_template('consultant_profile.html', consultant=consultant)

@app.route('/consultancy/register', methods=['GET','POST'])
@login_required
def register_consultant():
    categories = Category.query.filter_by(module='consultancy').all()
    if request.method == 'POST':
        expertise = request.form.get('expertise'); cats = request.form.get('categories'); bio = request.form.get('bio')
        c = Consultant(user_id=current_user.id, expertise=expertise, categories=cats, bio=bio, approved=False)
        db.session.add(c); db.session.commit(); flash('Application submitted for approval.', 'info')
        return redirect(url_for('consultancy_home'))
    return render_template('register_consultant.html', categories=categories)

# ---------------- Shop ----------------
@app.route('/shop')
def shop_home():
    categories = Category.query.filter_by(module='shop').all()
    q = request.args.get('q',''); base = Product.query
    if q: base = base.filter(Product.name.ilike(f"%{q}%"))
    items = paginate(base.order_by(Product.id.desc()), per_page=12)
    return render_template('shop_home.html', categories=categories, products=items.items)

@app.route('/shop/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(Product.category_id==product.category_id, Product.id!=product.id).limit(4).all()
    return render_template('product_detail.html', product=product, related=related)

# Session cart (legacy)
def _get_cart():
    cart = session.get('cart', {})
    return {int(pid): {'qty': data['qty']} for pid, data in cart.items()}

def _save_cart(cart):
    session['cart'] = {str(pid): {'qty': data['qty']} for pid, data in cart.items()}

@app.route('/shop/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    Product.query.get_or_404(product_id)
    qty = request.form.get('quantity', 1, type=int)
    cart = _get_cart(); cart[product_id] = {'qty': cart.get(product_id, {'qty':0})['qty'] + qty}; _save_cart(cart)
    flash('Product added to cart!', 'success'); return redirect(url_for('cart'))

@app.route('/shop/cart')
def cart():
    cart = _get_cart(); items, total = [], 0
    for pid, data in cart.items():
        prod = Product.query.get(pid)
        if not prod: continue
        subtotal = prod.price * data['qty']; total += subtotal
        items.append({'product': prod, 'quantity': data['qty'], 'price': prod.price})
    return render_template('cart.html', cart={'lines': items, 'total': total})

@app.route('/cart/update/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    qty = max(1, request.form.get('quantity', 1, type=int))
    cart = _get_cart()
    if product_id in cart: cart[product_id]['qty'] = qty
    _save_cart(cart); return redirect(url_for('cart'))

@app.route('/cart/remove/<int:product_id>', methods=['POST'])
def remove_cart(product_id):
    cart = _get_cart(); cart.pop(product_id, None); _save_cart(cart); return redirect(url_for('cart'))

# DB cart
def _ensure_cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id); db.session.add(cart); db.session.commit()
    return cart

@app.route('/db/cart')
@login_required
def db_cart():
    cart = _ensure_cart(); total = sum(i.price * i.quantity for i in cart.items)
    return render_template('cart.html', cart={'lines': [{'product': i.product, 'quantity': i.quantity, 'price': i.price} for i in cart.items], 'total': total})

@app.route('/db/add-to-cart/<int:product_id>', methods=['POST'])
@login_required
def db_add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    qty = request.form.get('quantity', 1, type=int)
    inv = Inventory.query.filter_by(product_id=product.id).first()
    if inv and inv.stock < qty:
        flash('Insufficient stock', 'danger'); return redirect(url_for('product_detail', product_id=product.id))
    cart = _ensure_cart(); item = next((i for i in cart.items if i.product_id==product.id), None)
    if item: item.quantity += qty
    else: db.session.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=qty, price=product.price))
    if inv: inv.stock -= qty
    db.session.commit(); flash('Added to cart', 'success'); return redirect(url_for('db_cart'))

@app.route('/shop/checkout', methods=['GET','POST'])
@login_required
def checkout():
    cart = _get_cart()
    if request.method == 'POST':
        items, total = [], 0
        for pid, data in cart.items():
            prod = Product.query.get(pid)
            if not prod: continue
            subtotal = prod.price * data['qty']; total += subtotal
            items.append((prod, data['qty'], prod.price))
        order = Order(user_id=current_user.id, total=total, status='placed')
        db.session.add(order); db.session.flush()
        for prod, qty, price in items:
            db.session.add(OrderItem(order_id=order.id, product_id=prod.id, quantity=qty, price=price))
        db.session.commit(); session.pop('cart', None)
        return redirect(url_for('order_confirmation'))
    items, total = [], 0
    for pid, data in cart.items():
        prod = Product.query.get(pid)
        if not prod: continue
        total += prod.price * data['qty']
        items.append({'product': prod, 'quantity': data['qty'], 'price': prod.price})
    return render_template('checkout.html', cart={'items': items, 'total': total})

@app.route('/shop/order-confirmation')
@login_required
def order_confirmation():
    order = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).first()
    return render_template('order_confirmation.html', order=order)

@app.route('/shop/orders')
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('order_history.html', orders=orders)

@app.route('/shop/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template('order_detail.html', order=order)

# ---------------- Password Change (logged-in) ----------------
@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm = request.form.get('confirm_password')
        if not current_user.check_password(old_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('change_password'))
        if not new_password or new_password != confirm:
            flash('New password and confirmation must match.', 'warning')
            return redirect(url_for('change_password'))
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('profile', user_id=current_user.id))
    return render_template('change_password.html', show_old=True)

# ---------------- Admin Dashboard ----------------
@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
@roles_required('admin')
def admin_dashboard():
    stats = {
        'total_users': User.query.count(),
        'total_products': Product.query.count(),
        'total_orders': Order.query.count(),
        'pending_orders': Order.query.filter_by(status='placed').count(),
        'total_revenue': db.session.query(db.func.sum(Order.total)).scalar() or 0,
        'total_threads': ForumThread.query.count(),
        'total_blogs': BlogPost.query.count(),
        'pending_consultants': Consultant.query.filter_by(approved=False).count(),
    }
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    pending = {
        'consultants': Consultant.query.filter_by(approved=False).count(),
        'products': 0
    }
    
    return render_template('admin_dashboard.html', stats=stats, recent_orders=recent_orders, pending=pending)

# ---------------- Admin Actions ----------------
@app.route('/admin/consultants/approve/<int:cid>', methods=['POST'])
@login_required
@roles_required('admin')
def admin_consultant_approve(cid):
    c = Consultant.query.get_or_404(cid); c.approved = True; db.session.commit(); flash('Consultant approved', 'success')
    return redirect(url_for('admin_consultants'))

@app.route('/admin/products/toggle/<int:pid>', methods=['POST'])
@login_required
@roles_required('admin')
def admin_product_toggle(pid):
    p = Product.query.get_or_404(pid); p.active = not p.active; db.session.commit(); flash('Product status updated', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/forum/delete-thread/<int:tid>', methods=['POST'])
@login_required
@roles_required('admin')
def admin_delete_thread(tid):
    t = ForumThread.query.get_or_404(tid); db.session.delete(t); db.session.commit(); flash('Thread deleted', 'warning')
    return redirect(url_for('admin_forum'))

@app.route('/admin/knowledge/delete-blog/<int:bid>', methods=['POST'])
@login_required
@roles_required('admin')
def admin_delete_blog(bid):
    b = BlogPost.query.get_or_404(bid); db.session.delete(b); db.session.commit(); flash('Blog deleted', 'warning')
    return redirect(url_for('admin_knowledge'))

@app.route('/admin/categories', methods=['GET','POST'])
@login_required
@roles_required('admin')
def admin_categories():
    if request.method == 'POST':
        name = request.form.get('name'); module = request.form.get('module'); desc = request.form.get('description','')
        if name and module:
            db.session.add(Category(name=name, module=module, description=desc)); db.session.commit(); flash('Category saved', 'success')
    categories = Category.query.order_by(Category.module, Category.name).all()
    return render_template('admin_categories.html', categories=categories)

@app.route('/admin/users')
@login_required
@roles_required('admin')
def admin_users():
    users = User.query.order_by(User.join_date.desc()).all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/products')
@login_required
@roles_required('admin')
def admin_products():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template('admin_products.html', products=products)

@app.route('/admin/products/add', methods=['GET','POST'])
@login_required
@roles_required('admin')
def add_product():
    categories = Category.query.filter_by(module='shop').all()
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price', type=float)
        category_id = request.form.get('category_id', type=int)
        image = request.form.get('image', '/static/images/default-product.jpg')
        
        if name and price and category_id:
            product = Product(
                name=name,
                description=description,
                price=price,
                category_id=category_id,
                image=image,
                active=True,
                rating=0
            )
            db.session.add(product)
            db.session.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin_products'))
        else:
            flash('Please fill all required fields', 'danger')
    
    return render_template('add_product.html', categories=categories)

@app.route('/admin/products/edit/<int:product_id>', methods=['GET','POST'])
@login_required
@roles_required('admin')
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.filter_by(module='shop').all()
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.price = request.form.get('price', type=float)
        product.category_id = request.form.get('category_id', type=int)
        image = request.form.get('image')
        if image:
            product.image = image
        
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('edit_product.html', product=product, categories=categories)

@app.route('/admin/orders')
@login_required
@roles_required('admin')
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/forum')
@login_required
@roles_required('admin')
def admin_forum():
    threads = ForumThread.query.order_by(ForumThread.created_at.desc()).all()
    return render_template('admin_forum.html', threads=threads)

@app.route('/admin/knowledge')
@login_required
@roles_required('admin')
def admin_knowledge():
    blogs = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin_knowledge.html', blogs=blogs)

@app.route('/admin/consultants')
@login_required
@roles_required('admin')
def admin_consultants():
    consultants = Consultant.query.order_by(Consultant.id.desc()).all()
    return render_template('admin_consultants.html', consultants=consultants)

@app.route('/admin/reports')
@login_required
@roles_required('admin')
def admin_reports():
    return render_template('admin_reports.html')

# ---------------- Errors & Utility ----------------
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

# Optional route map (remove in prod)
@app.route('/_routes')
def _routes():
    return {'routes': sorted([(r.rule, r.endpoint) for r in app.url_map.iter_rules()])}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
