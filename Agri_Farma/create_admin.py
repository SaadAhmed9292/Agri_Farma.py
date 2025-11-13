from app import app
from models import db, Role, User, Profile

with app.app_context():
    # Check if user already exists
    existing = User.query.filter_by(email='admin@gmail.com').first()
    if existing:
        print('User admin@gmail.com already exists!')
        print('Email: admin@gmail.com')
        print('Password: admin123')
    else:
        # Get or create admin role
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            db.session.add(admin_role)
        
        # Create admin user
        admin = User(name='Admin', email='admin@gmail.com')
        admin.set_password('admin123')
        admin.roles.append(admin_role)
        db.session.add(admin)
        db.session.flush()
        
        # Create profile
        db.session.add(Profile(
            user_id=admin.id,
            city='',
            state='',
            country='',
            profession='admin',
            expertise='expert'
        ))
        
        db.session.commit()
        print('✅ Admin account created successfully!')
        print('Email: admin@gmail.com')
        print('Password: admin123')
