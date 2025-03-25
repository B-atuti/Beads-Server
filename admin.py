from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from models import db, User
from werkzeug.security import generate_password_hash
import bcrypt

admin_bp = Blueprint("admin", __name__)

def create_admin_user():
    with db.session.begin():
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            new_admin = User(username="admin", password=hashed_password, role="admin")
            db.session.add(new_admin)
            db.session.commit()
            print("✅ Default Admin Created: admin / admin123")

@admin_bp.route("/login", methods=["POST"])
def login():
    """Admin & Employee Login Endpoint"""
    data = request.json

    user = User.query.filter_by(username=data.get("username")).first()

    if not user:
        print("❌ User not found")
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.checkpw(data["password"].encode('utf-8'), user.password.encode('utf-8')):
        print("❌ Incorrect password")
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity={"username": user.username, "role": user.role}, fresh=True)
    refresh_token = create_refresh_token(identity={"username": user.username, "role": user.role})

    print("✅ Login successful")
    return jsonify({"access_token": access_token, "refresh_token": refresh_token, "role": user.role})

@admin_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)  # ✅ Requires a valid refresh token
def refresh_token():
    """Generate a new access token using the refresh token"""
    identity = get_jwt_identity()
    new_access_token = create_access_token(identity=identity, fresh=False)
    return jsonify({"access_token": new_access_token})


@admin_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """Reset Password for Admin or Employee"""
    data = request.json
    
    # Validate input
    if not data.get("username") or not data.get("new_password"):
        return jsonify({"error": "Username and new password are required"}), 400
    
    user = User.query.filter_by(username=data["username"]).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Hash the new password
    hashed_new_password = bcrypt.hashpw(data["new_password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Update password in the database
    user.password = hashed_new_password
    db.session.commit()
    
    return jsonify({"message": "Password reset successfully"}), 200
