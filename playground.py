from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from models import db, Notification

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://your_user:your_password@localhost/your_database"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ✅ Fetch notifications (GET)
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    notifications = Notification.query.order_by(Notification.timestamp.desc()).all()
    return jsonify([n.to_dict() for n in notifications])

# ✅ Add a new notification (POST)
@app.route('/api/notifications', methods=['POST'])
def create_notification():
    data = request.json
    if 'message' not in data:
        return jsonify({"error": "Message is required"}), 400

    new_notification = Notification(message=data['message'])
    db.session.add(new_notification)
    db.session.commit()

    return jsonify(new_notification.to_dict()), 201

# ✅ Mark notification as read (PATCH)
@app.route('/api/notifications/<int:id>/read', methods=['PATCH'])
def mark_notification_as_read(id):
    notification = Notification.query.get(id)
    if not notification:
        return jsonify({"error": "Notification not found"}), 404

    notification.read_status = True
    db.session.commit()
    return jsonify(notification.to_dict())

# ✅ Delete a notification (DELETE)
@app.route('/api/notifications/<int:id>', methods=['DELETE'])
def delete_notification(id):
    notification = Notification.query.get(id)
    if not notification:
        return jsonify({"error": "Notification not found"}), 404

    db.session.delete(notification)
    db.session.commit()
    return jsonify({"message": "Notification deleted successfully"})
