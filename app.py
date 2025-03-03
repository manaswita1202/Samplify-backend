from flask import Flask, request, jsonify,send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import random
import os

app = Flask(__name__)

# Enable CORS
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# MySQL Database Configuration (Using SQLAlchemy)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:root@localhost/samplify'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'ashirwad'  # Change this to a secure secret key

db = SQLAlchemy(app)
jwt = JWTManager(app)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%d/%m/%Y')  # Convert to DD/MM/YYYY
        return super().default(obj)

app.json_encoder = CustomJSONEncoder  # Apply custom encoder

# ---------------- User Model ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

# ---------------- Style Model ----------------
class Style(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    style_number = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    sample_type = db.Column(db.String(50), nullable=False)
    garment = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    smv = db.Column(db.Float, nullable=True)
    buyer_approval = db.Column(db.Boolean, nullable=True)
    order_received_date = db.Column(db.Date, nullable=True)
    order_delivery_date = db.Column(db.Date, nullable=True)
    approval_status = db.Column(db.Enum("received", "pending", "yetToSend","queued"), default="queued")
    lab_dips_enabled = db.Column(db.Boolean, nullable=True)
    techpack_data = db.Column(db.JSON, nullable=True)  # JSON column added

    def to_dict(self):
        return {
            "id": self.id,
            "style": self.style_number,
            "buyer": self.brand,
            "garment": self.garment,
            "date": self.order_received_date    ,
            "approvalStatus": self.approval_status,
        }


# ---------------- Activity Model ----------------
class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    style = db.Column(db.String(50), nullable=False)
    process = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Float, nullable=False)
    planned_start = db.Column(db.String(20), nullable=True)
    planned_end = db.Column(db.String(20), nullable=True)
    actual_start = db.Column(db.String(20), nullable=True)
    actual_end = db.Column(db.String(20), nullable=True)
    actual_duration = db.Column(db.Float, nullable=True)
    delay = db.Column(db.Float, nullable=True)
    responsibility = db.Column(db.String(50), nullable=False)
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    style_number = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    sample_type = db.Column(db.String(50), nullable=False)
    garment = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="toBeDone")
    progress = db.Column(db.Integer, default=0)
    priority = db.Column(db.String(20), default="Medium")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    comment = db.Column(db.Text, nullable=True)
    problem_reported = db.Column(db.Boolean, default=False)

    steps = db.relationship("TaskStep", backref="task", cascade="all, delete", lazy=True)

# Task Step Model
class TaskStep(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    step_name = db.Column(db.String(50), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)

class Courier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    style_number = db.Column(db.String(50), nullable=False)
    courier_name = db.Column(db.String(100), nullable=False)
    awb_number = db.Column(db.String(50), nullable=False)
    att = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(255), nullable=False)
    garment_type = db.Column(db.String(50), nullable=False)
    placement_date = db.Column(db.DateTime, default=datetime.utcnow)
    completion_date = db.Column(db.DateTime, nullable=True)

# Order Status Model
class OrderStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    courier_id = db.Column(db.Integer, db.ForeignKey('courier.id'), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    placement_date = db.Column(db.DateTime, default=datetime.utcnow)
    completion_date = db.Column(db.DateTime, nullable=True)

class LabDip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    style_number = db.Column(db.String(50), nullable=False)
    buyer = db.Column(db.String(50))
    fabric = db.Column(db.String(50))
    color = db.Column(db.String(50))
    shade = db.Column(db.String(10), default='A')
    status = db.Column(db.Enum('approved', 'pending', 'yetToSend'), default='yetToSend')
    approval_date = db.Column(db.Date)

    def to_dict(self):
        return {
            "id": self.id,
            "style": self.style_number,
            "buyer": self.buyer,
            "fabric": self.fabric,
            "color": self.color,
            "shade": self.shade,
            "status": self.status,
            "date": self.approval_date.strftime('%d/%m/%Y') if self.approval_date else None
        }

class Trim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    image = db.Column(db.String(255), nullable=True)
    composition = db.Column(db.String(255), nullable=True)
    structure = db.Column(db.String(255), nullable=True)
    shade = db.Column(db.String(255), nullable=True)
    brand = db.Column(db.String(255), nullable=True)
    code = db.Column(db.String(255), nullable=True)

class TrimVariant(db.Model):
    __tablename__ = 'trim_variants'
    id = db.Column(db.Integer, primary_key=True)
    trim_id = db.Column(db.Integer)
    image = db.Column(db.String(255), nullable=False)
    composition = db.Column(db.String(255))
    structure = db.Column(db.String(255))
    shade = db.Column(db.String(255))
    brand = db.Column(db.String(255))
    code = db.Column(db.String(255))


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read_status = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "read_status": self.read_status
        }



PREDEFINED_PROCESSES = [
    {"process": "Order Receipt (Buyer PO)", "duration": 0, "responsibility": "Merchandiser"},
    {"process": "CAD Consumption Received", "duration": 2, "responsibility": "CAD Department"},
    {"process": "BOM Generation", "duration": 0.5, "responsibility": "Merchandiser"},
    {"process": "PO Issue for Fabric & Trims", "duration": 0.5, "responsibility": "Merchandiser"},
    {"process": "Fabric Received", "duration": 34, "responsibility": "Store Manager"},
    {"process": "Sample Indent Made", "duration": 0.5, "responsibility": "Merchandiser"},
    {"process": "Pattern Cutting", "duration": 0.5, "responsibility": "Pattern Master"},
    {"process": "Sewing", "duration": 4, "responsibility": "Production Head"},
    {"process": "Embroidery", "duration": 0.5, "responsibility": "Embroidery Head"},
    {"process": "Finishing", "duration": 0.5, "responsibility": "Production Head"},
    {"process": "Packing", "duration": 1, "responsibility": "Production Head"},
    {"process": "Documentation in PLM", "duration": 0.5, "responsibility": "Production Head"},
    {"process": "Dispatch", "duration": 0.5, "responsibility": "Merchandiser"},
]

# Create tables in the database
with app.app_context():
    db.create_all()

# ---------------- Authentication Routes ----------------
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "User already exists"}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({"access_token": access_token}), 200

# ---------------- Styles Routes (Using SQLAlchemy) ----------------
@app.route('/styles', methods=['GET'])
def get_styles():
    styles = Style.query.all()
    return jsonify([{
        "id": s.id,
        "styleNumber": s.style_number,
        "brand": s.brand,
        "sampleType": s.sample_type,
        "garment": s.garment,
        "color": s.color,
        "quantity": s.quantity,
        "smv": s.smv,
        "buyerApproval": s.buyer_approval,
        "orderReceivedDate": s.order_received_date.strftime("%Y-%m-%d") if s.order_received_date else None,
        "orderDeliveryDate": s.order_delivery_date.strftime("%Y-%m-%d") if s.order_delivery_date else None,
        "labDipsEnabled" : s.lab_dips_enabled,
        "techpackData" : s.techpack_data
    } for s in styles])

@app.route('/styles', methods=['POST'])
def add_style(): 
    data = request.json
    new_style = Style(
        style_number=data['styleNumber'],
        brand=data['brand'],
        sample_type=data['sampleType'],
        garment=data['garment'],
        color=data['color'],
        quantity=data['quantity'],
        smv=data.get('smv'),
        buyer_approval=data.get('buyerApproval'),
        order_received_date=datetime.strptime(data['orderReceivedDate'], "%Y-%m-%d") if data.get('orderReceivedDate') else None,
        order_delivery_date=datetime.strptime(data['orderDeliveryDate'], "%Y-%m-%d") if data.get('orderDeliveryDate') else None,
        lab_dips_enabled = data.get("labDipsEnabled")
    )
    db.session.add(new_style)
    db.session.commit()
    new_task = Task(
        style_number=data["styleNumber"],
        brand=data["brand"],
        sample_type=data["sampleType"],
        garment=data["garment"],
        status=data.get("status", "toBeDone"),
    )
    db.session.add(new_task)
    db.session.commit()
    # Add steps for the task
    steps = ["Start","Indent","PatternCutting","FabricCutting","Sewing","Embroidery","Finishing", "Problem"]
    # steps = ["start", "indent", "pattern", "fabric", "embroidery", "packing", "problem"]
    for step in steps:
        db.session.add(TaskStep(task_id=new_task.id, step_name=step, is_completed=False))
    db.session.commit()
    if data.get("labDipsEnabled") == True:
        new_lab_dip = LabDip(
        style_number=data['styleNumber'],
        buyer=data['brand'],
        fabric=data.get('fabric', 'Cotton Blend'),
        color=data['color'],
        shade=data.get('shade', 'A'),
        status=data.get('status', 'yetToSend'),
        approval_date=datetime.strptime(data['date'], '%d/%m/%Y') if 'date' in data else None
    )
        db.session.add(new_lab_dip)
        db.session.commit()


    return jsonify({"message": "Style added successfully", "id": new_style.id}), 201

@app.route('/styles/<int:style_id>', methods=['PUT'])
def update_style(style_id):
    style = Style.query.get(style_id)
    if not style:
        return jsonify({"error": "Style not found"}), 404
    data = request.json
    style.style_number = data.get('styleNumber', style.style_number)
    style.brand = data.get('brand', style.brand)
    style.sample_type = data.get('sampleType', style.sample_type)
    style.garment = data.get('garment', style.garment)
    style.color = data.get('color', style.color)
    style.quantity = data.get('quantity', style.quantity)
    style.smv = data.get('smv', style.smv)
    style.buyer_approval = data.get('buyerApproval', style.buyer_approval)
    style.order_received_date = datetime.strptime(data['orderReceivedDate'], "%Y-%m-%d") if data.get('orderReceivedDate') else style.order_received_date
    style.order_delivery_date = datetime.strptime(data['orderDeliveryDate'], "%Y-%m-%d") if data.get('orderDeliveryDate') else style.order_delivery_date
    style.lab_dips_enabled = data.get("labDipsEnabled", style.lab_dips_enabled)
    if(style.buyer_approval):
        style.approval_status = "received"
    db.session.commit()

    task = Task.query.filter(Task.style_number == style.style_number).first()
    if task is None:
        new_task = Task(
        style_number=data["styleNumber"],
        brand=data["brand"],
        sample_type=data["sampleType"],
        garment=data["garment"],
        status=data.get("status", "toBeDone"),
        )
        db.session.add(new_task)
        db.session.commit()
        # Add steps for the task
        steps = ["Start","Indent","PatternCutting","FabricCutting","Sewing","Embroidery","Finishing", "Problem"]
        # steps = ["start", "indent", "pattern", "fabric", "embroidery", "packing", "problem"]
        for step in steps:
            db.session.add(TaskStep(task_id=new_task.id, step_name=step, is_completed=False))
        db.session.commit()


    if data.get("labDipsEnabled") == True:
        new_lab_dip = LabDip(
        style_number=style.style_number,
        buyer=style.brand,
        fabric=style.garment,
        color=style.color,
        shade=data.get('shade', 'A'),
        status=data.get('status', 'yetToSend'),
        approval_date=datetime.strptime(style.order_received_date, '%d/%m/%Y') if 'date' in data else None
        )
        db.session.add(new_lab_dip)
        db.session.commit()

    return jsonify({"message": "Style updated successfully"}), 200

# ---------------- Activity Routes (Using SQLAlchemy) ----------------
@app.route("/api/activity", methods=["GET"])
def get_activities():
    style = request.args.get("style")
    if not style:
        return jsonify({"error": "Style parameter is required"}), 400

    activities = Activity.query.filter_by(style=style).all()
    if not activities:
        return jsonify({"message": "No activities found for the given style"}), 404

    return jsonify([
        {
            "id": act.id,
            "style": act.style,
            "process": act.process,
            "duration": act.duration,
            "plannedStart": act.planned_start.strftime("%Y-%m-%d") if act.planned_start else None,
            "plannedEnd": act.planned_end.strftime("%Y-%m-%d") if act.planned_end else None,
            "actualStart": act.actual_start.strftime("%Y-%m-%d") if act.actual_start else None,
            "actualEnd": act.actual_end.strftime("%Y-%m-%d") if act.actual_end else None,
            "actualDuration": act.actual_duration,
            "delay": act.delay,
            "responsibility": act.responsibility
        } 
        for act in activities
    ])

@app.route("/api/activity", methods=["POST"])
def add_activities():
    data = request.json
    style = data.get("style")
    received_date = data.get("receivedDate")

    if not style:
        return jsonify({"error": "Style is required"}), 400
    if not received_date:
        return jsonify({"error": "Received Date is required"}), 400

    # Check if activities for this style already exist
    if Activity.query.filter_by(style=style).first():
        return jsonify({"message": "Activities for this style already exist"}), 400

    try:
        planned_start = datetime.strptime(received_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    for process in PREDEFINED_PROCESSES:
        planned_end = planned_start + timedelta(days=process["duration"])

        new_activity = Activity(
            style=style,
            process=process["process"],
            duration=process["duration"],
            planned_start=planned_start.strftime("%Y-%m-%d"),
            planned_end=planned_end.strftime("%Y-%m-%d"),
            actual_start=None,
            actual_end=None,
            actual_duration=None,
            delay=None,
            responsibility=process["responsibility"]
        )

        db.session.add(new_activity)
        planned_start = planned_end  # Update for next process

    db.session.commit()
    return jsonify({"message": "Activities initialized for style"}), 201

@app.route("/api/activity/<int:id>", methods=["PUT"])
def update_activity(id):
    activity = Activity.query.get_or_404(id)

    data = request.json
    actual_start = data.get("actualStart")
    actual_end = data.get("actualEnd")

    if actual_start:
        try:
            actual_start_date = datetime.strptime(actual_start, "%Y-%m-%d")
            activity.actual_start = actual_start
        except ValueError:
            return jsonify({"error": "Invalid actual_start format. Use YYYY-MM-DD"}), 400

    if actual_end:
        try:
            actual_end_date = datetime.strptime(actual_end, "%Y-%m-%d")
            activity.actual_end = actual_end
        except ValueError:
            return jsonify({"error": "Invalid actual_end format. Use YYYY-MM-DD"}), 400

    if activity.actual_start and activity.actual_end:
        start_date = (activity.actual_start)
        end_date = (activity.actual_end)
        activity.actual_duration = (end_date - start_date).days

        if activity.planned_end:
            planned_end_date = (activity.planned_end)
            activity.delay = max((end_date - planned_end_date).days, 0)

    db.session.commit()
    return jsonify({"message": "Activity updated successfully"}), 200

@app.route("/api/approval-status", methods=["GET"])
def get_approval_status():
    styles = Style.query.all()
    
    categorized_samples = {"received": [], "pending": [], "yetToSend": [], "queued" : []}
    
    for style in styles:
        categorized_samples[style.approval_status].append(style.to_dict())

    return jsonify(categorized_samples)

# API to update approval status of a style
@app.route("/api/update-status", methods=["POST"])
def update_status():
    data = request.json
    style_id = data.get("id")
    new_status = data.get("approvalStatus")

    if new_status not in ["received", "pending", "yetToSend"]:
        return jsonify({"error": "Invalid status"}), 400

    style = Style.query.get(style_id)
    if not style:
        return jsonify({"error": "Style not found"}), 404

    style.approval_status = new_status
    db.session.commit()

    return jsonify({"message": "Status updated successfully", "style": style.to_dict()})

@app.route("/tasks", methods=["POST"])
def add_task():
    data = request.json
    new_task = Task(
        style_number=data["styleNumber"],
        brand=data["brand"],
        sample_type=data["sampleType"],
        garment=data["garment"],
        status=data.get("status", "toBeDone"),
    )
    db.session.add(new_task)
    db.session.commit()

    # Add steps for the task
    # steps = ["start", "indent", "pattern", "fabric", "embroidery", "packing", "problem"]
    steps = ["Start","Indent","PatternCutting","FabricCutting","Sewing","Embroidery","Finishing", "Problem"]

    for step in steps:
        db.session.add(TaskStep(task_id=new_task.id, step_name=step, is_completed=False))
    db.session.commit()

    return jsonify({"message": "Task added successfully", "task_id": new_task.id}), 201

# Get all tasks
@app.route("/tasks", methods=["GET"])
def get_tasks():
    tasks = Task.query.all()
    task_list = []
    for task in tasks:
        task_list.append({
            "id": task.id,
            "styleNumber": task.style_number,
            "brand": task.brand,
            "sampleType": task.sample_type,
            "garment": task.garment,
            "status": task.status,
            "progress": task.progress,
            "priority": task.priority,
            "timestamp": task.timestamp,
            "comment": task.comment,
            "problemReported": task.problem_reported,
            "steps": {step.step_name: step.is_completed for step in task.steps}
        })
    return jsonify(task_list)

# Get a single task
@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    task_data = {
        "id": task.id,
        "styleNumber": task.style_number,
        "brand": task.brand,
        "sampleType": task.sample_type,
        "garment": task.garment,
        "status": task.status,
        "progress": task.progress,
        "priority": task.priority,
        "timestamp": task.timestamp,
        "comment": task.comment,
        "problemReported": task.problem_reported,
        "steps": {step.step_name: step.is_completed for step in task.steps},
    }
    return jsonify(task_data)

# Update a task (progress, status, steps, comments)
@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    data = request.json
    if "status" in data:
        task.status = data["status"]
    if "progress" in data:
        task.progress = data["progress"]
    if "comment" in data:
        task.comment = data["comment"]
    if "problemReported" in data:
        task.problem_reported = data["problemReported"]

    # Update steps
    if "steps" in data:
        for step_name, is_completed in data["steps"].items():
            step = TaskStep.query.filter_by(task_id=task_id, step_name=step_name).first()
            if step:
                step.is_completed = is_completed

    db.session.commit()
    if "status" in data and data["status"] == "completed":
        courier = Courier(
        style_number=task.style_number,
        courier_name="Blue Dart",
        awb_number="#2025" + str(random.randint(1,20000)),
        att="#ASJK" + str(random.randint(1,50)),
        content=task.sample_type,
        garment_type=task.garment
    )
        db.session.add(courier)
        db.session.commit()

        for order_type in ['Booked Portal', 'Sent from Factory', 'In Transit', 'Received']:
            order_status = OrderStatus(
                courier_id=courier.id,
                type=order_type
            )
            db.session.add(order_status)
        
        db.session.commit()
        style = Style.query.filter_by(style_number=task.style_number).first()
        if style is not None:
            style.approval_status = "yetToSend"
            db.session.commit()
        

    return jsonify({"message": "Task updated successfully"})

# Delete a task
@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted successfully"})

@app.route('/add_courier', methods=['POST'])
def add_courier():
    data = request.json
    courier = Courier(
        style_number=data['styleNumber'],
        courier_name=data['courierName'],
        awb_number=data['awbNumber'],
        att=data['att'],
        content=data['content'],
        garment_type=data['garmentType']
    )
    db.session.add(courier)
    db.session.commit()

    for order_type in ['Booked Portal', 'Sent from Factory', 'In Transit', 'Received']:
        order_status = OrderStatus(
            courier_id=courier.id,
            type=order_type
        )
        db.session.add(order_status)
    
    db.session.commit()
    return jsonify({'message': 'Courier added successfully'}), 201

@app.route('/get_couriers', methods=['GET'])
def get_couriers():
    couriers = Courier.query.all()
    result = []
    for courier in couriers:
        orders = OrderStatus.query.filter_by(courier_id=courier.id).all()
        order_list = [
            {
                "id": order.id,
                "type": order.type,
                "completed": order.completed,
                "placement": order.placement_date.strftime('%d/%m/%Y'),
                "date": order.completion_date
            }
            for order in orders
        ]
        result.append({
            "id": courier.id,
            "styleNumber": courier.style_number,
            "courierName": courier.courier_name,
            "awbNumber": courier.awb_number,
            "att": courier.att,
            "content": courier.content,
            "garmentType": courier.garment_type,
            "placement": courier.placement_date,
            "date": courier.completion_date,
            "orders": order_list
        })
    return jsonify(result), 200

@app.route('/update_order', methods=['POST'])
def update_order():
    data = request.json
    order_id = data.get('orderId')  # Extract orderId
    completed = data.get('completed')

    if order_id is None or completed is None:
        return jsonify({'error': 'Missing required fields'}), 400

    order = OrderStatus.query.get(order_id)

    if not order:
        return jsonify({'error': 'Order not found'}), 404

    # Update order status
    order.completed = completed
    order.completion_date = datetime.utcnow() if completed else None

    db.session.commit()
    if order.type=="Sent from Factory":
        courier = Courier.query.filter_by(id=order.courier_id).first()
        style = Style.query.filter_by(style_number=courier.style_number)
        style.approval_status = "pending"
        db.session.add(style)
        db.session.commit()

    return jsonify({
        'message': 'Order updated successfully',
        'orderId': order.id,
        'completed': order.completed,
        'completionDate': order.completion_date.strftime('%d/%m/%Y') if order.completion_date else None
    }), 200

@app.route('/delete_courier/<int:courier_id>', methods=['DELETE'])
def delete_courier(courier_id):
    courier = Courier.query.get(courier_id)
    if courier:
        OrderStatus.query.filter_by(courier_id=courier_id).delete()
        db.session.delete(courier)
        db.session.commit()
        return jsonify({'message': 'Courier deleted successfully'}), 200
    return jsonify({'error': 'Courier not found'}), 404

@app.route('/lab_dips', methods=['GET'])
def get_lab_dips():
    lab_dips = LabDip.query.all()
    response = {
        "approved": [dip.to_dict() for dip in lab_dips if dip.status == "approved"],
        "pending": [dip.to_dict() for dip in lab_dips if dip.status == "pending"],
        "yetToSend": [dip.to_dict() for dip in lab_dips if dip.status == "yetToSend"]
    }
    return jsonify(response), 200

@app.route('/lab_dips', methods=['POST'])
def add_lab_dip():
    data = request.json
    style = Style.query.filter_by(style_no=data['style']).first()
    
    if not style:
        style = Style(style_no=data['style'])
        db.session.add(style)
        db.session.commit()

    new_lab_dip = LabDip(
        style_id=style.id,
        buyer=data['buyer'],
        fabric=data['fabric'],
        color=data['color'],
        shade=data.get('shade', 'A'),
        status=data.get('status', 'yetToSend'),
        approval_date=datetime.strptime(data['date'], '%d/%m/%Y') if 'date' in data else None
    )
    db.session.add(new_lab_dip)
    db.session.commit()

    return jsonify({"message": "Lab Dip added successfully"}), 201

@app.route('/lab_dips/<int:dip_id>/status', methods=['PUT'])
def update_lab_dip_status(dip_id):
    data = request.json
    lab_dip = LabDip.query.get(dip_id)
    
    if not lab_dip:
        return jsonify({"error": "Lab Dip not found"}), 404

    lab_dip.status = data['status']
    if data['status'] == 'approved':
        lab_dip.approval_date = datetime.utcnow()

    db.session.commit()
    return jsonify({"message": "Lab Dip status updated successfully"}), 200

app.config["UPLOAD_FOLDER"] = "uploads"

@app.route("/upload_files", methods=["POST"])
def upload_files():
    buyer_name = request.form.get("buyerName")
    garment = request.form.get("garment")

    if not buyer_name or not garment:
        return jsonify({"message": "Buyer Name and Garment are required!"}), 400

    uploaded_files = {}
    for file_key in ["techpack", "bom", "specSheet"]:
        if file_key in request.files:
            file = request.files[file_key]
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], buyer_name + "_" + garment + "_" + file.filename )
            file.save(file_path)
            uploaded_files[file_key] = file_path

    # If a Techpack file was uploaded, create a new Style entry
    if "techpack" in uploaded_files:
        new_style = Style(
            style_number="EBOLT-S-05",
            brand=buyer_name,
            sample_type="Fit Sample",
            garment=garment,
            color="Ivory",
            quantity="2",
            smv="42",
            order_received_date=datetime.today(),
            techpack_data = generateTechPackData()
        )
        db.session.add(new_style)
        db.session.commit()

        # style_number_to_update = new_style.style_number
        # new_techpack_data = {
        #     "fabric": "Linen",
        #     "buttons": 5,
        #     "zippers": 1
        # }

        # db.session.query(Style).filter_by(style_number=style_number_to_update).update({
        #     "techpack_data": new_techpack_data
        # })
        # db.session.commit()


    return jsonify({"message": "Files uploaded successfully!", "files": uploaded_files})

def generateTechPackData():
         new_techpack_data = {
    "shade": "Ivory",
    "patternNo" : "290638",
    "season": "SS25",
    "mainBodyFabric": "Jersey Waffle 100% Cotton",
    "collarFabric": "",
    "mainLabel": "EA02A00319CH - WHITE/BLUE ",
    "threadShade": "BLACK, TKT120 ",
    "sweingThreads": "STIPBPLAHUB1019 ,STILASATHUB2424 ",
    "sweingThreadsDetails": "POLY POLY-2994-EPIC-Tex 24 - TKT 120 , POLY POLY-2994-EPIC-Tex 18 - TKT 180",
    "costSheet": {
        "fabricCost": [
        {
            "fabricType": "Shell Fabric",
            "description": "Jersey Waffle 100% Cotton "
        }
        ],
       "trimCost": [
      {
        "trim": "BUTTON ",
        "descirption": "20134935 - 4 Holes - Gritt ",
        "quantity" : "3"
      },
      {
        "trim": "Interlining",
        "descirption": "Fusible interlining 9510 ",
        "quantity" : "66"
      },
      {
        "trim": "pocket label",
        "descirption": "Brand label OUTSIDE FLAG LABEL ",
        "quantity" : "4.25"
      },
      {
        "trim": "SIZE ",
        "descirption": "Size label LEISURE HUGO BLUE ",
        "quantity" : "13.6"
      },
      {
        "trim": "Main label",
        "descirption": "Brand label 30X44 (59) MM ",
        "quantity" : "7.65"
      },
      {
        "trim": "Care label ",
        "descirption": "Care label BEDRUCKT 35mm Breite",
        "quantity" : "14.28"
      },
      {
        "trim": "COO LABEL",
        "descirption": "Made in India",
        "quantity" : "5"
      },
      {
        "trim": "Thread",
        "descirption": "POLY POLY-2994-EPIC-Tex 24 - TKT 120",
        "quantity" : "177"
      },
      {
        "trim": "Thread",
        "descirption": "POLY POLY-2994-EPIC-Tex 18 - TKT 180",
        "quantity" : "174"
      }
    ]
    },
    "bom": {
        "fabric": [
        {
            "code": "",
            "description": "Jersey Waffle 100% Cotton",
            "color": "Ivory",
            "size": "M",
            "quantity": "1"
        }
        ],
        "trims": [
        {
            "code": "STIINCOTGEN5877",
            "trim": "Interlining",
            "descirption": "Fusible interlining 9510 ",
            "color": "9510 COL.3216 BLACK",
            "size": "M",
            "quantity": "66.00"
        },
        {
            "code": "STILAWOVHUB4475",
            "trim": "pocket label",
            "descirption": "Brand label OUTSIDE FLAG LABEL",
            "color": "EA02A00319CH - WHITE/BLUE",
            "size": "M",
            "quantity": "4.25"
        },
        {
            "code": "SSTILAWOVHUB4649",
            "trim": "SIZE",
            "descirption": "Size label LEISURE HUGO BLUE",
            "color": "EA02A00319CH - WHITE/BLUE",
            "size": "M",
            "quantity": "13.60"
        },
        {
            "code": "STILAWOVHUB1267",
            "trim": "Main label",
            "descirption": "Brand label 30X44 (59) MM",
            "color": "EA02A00319CH - WHITE/BLUE",
            "size": "M",
            "quantity": "7.65"
        },
        {
            "code": "STISTPAPHUB8475",
            "trim": "Care label",
            "descirption": "Care label BEDRUCKT 35mm Breite",
            "color": "CL31 CL32",
            "size": "M",
            "quantity": "14.28"
        },
        {
            "code": "STIHTPAPHUB1228",
            "trim": "Coo Label",
            "descirption": "Made in India",
            "color": "CL31 CL32",
            "size": "M",
            "quantity": "5.00"
        },
        {
            "code": "STIPBPLAHUB1019",
            "trim": "Thread",
            "descirption": "POLY POLY-2994-EPIC-Tex 24 - TKT 120",
            "color": "2994-TEX-24-POLY POLY-SH-, BLACK, TKT120",
            "size": "M",
            "quantity": "177.00"
        },
        {
            "code": "STILASATHUB2424",
            "trim": "Thread",
            "descirption": "POLY POLY-2994-EPIC-Tex 18 - TKT 180",
            "color": "2994-TEX-24-POLY POLY-SH-, BLACK, TKT120",
            "size": "M",
            "quantity": "174.00"
        }
        ]
    }
        }
         return new_techpack_data


@app.route("/get_uploaded_files", methods=["GET"])
def get_uploaded_files():
    file_list = []
    upload_dir = app.config["UPLOAD_FOLDER"]
    
    for file_name in os.listdir(upload_dir):
        parts = file_name.split("_")
        if len(parts) >= 3:
            buyer_name, garment, file_type = parts[0], parts[1], parts[2]
            file_list.append({
                "buyerName": buyer_name,
                "garment": garment,
                "fileType": file_type,
                "filePath": f"/uploads/{file_name}"
            })
    
    return jsonify(file_list)


@app.route('/api/trims', methods=['GET'])
def get_trims():
    trims = Trim.query.all()
    return jsonify([{
        'id': trim.id,
        'name': trim.name,
        'image': trim.image,
        'composition': trim.composition,
        'structure': trim.structure,
        'shade': trim.shade,
        'brand': trim.brand,
        'code': trim.code
    } for trim in trims])

# Get a single trim by name
@app.route('/api/trims/<string:trim_name>', methods=['GET'])
def get_trim(trim_name):
    trim = Trim.query.filter_by(name=trim_name).first()
    if not trim:
        return jsonify({'error': 'Trim not found'}), 404
    trimVariants = TrimVariant.query.filter_by(trim_id = trim.id)
    variants = [
        {
            "id": variant.id,
            "image": variant.image,
            "composition": variant.composition,
            "structure": variant.structure,
            "shade": variant.shade,
            "brand": variant.brand,
            "code" : variant.code
        }
        for variant in trimVariants
    ]


    return jsonify({
        'id': trim.id,
        'name': trim.name,
        'image': trim.image,
        'composition': trim.composition,
        'structure': trim.structure,
        'shade': trim.shade,
        'brand': trim.brand,
        'code': trim.code,
        "variants": variants
    })

# Add a new trim
@app.route('/api/trims', methods=['POST'])
def add_trim():
    data = request.json
    new_trim = Trim(
        name=data['name'],
        image=data.get('image', ''),
        composition=data.get('composition', ''),
        structure=data.get('structure', ''),
        shade=data.get('shade', ''),
        brand=data.get('brand', ''),
        code=data.get('code', '')
    )
    db.session.add(new_trim)
    db.session.commit()
    return jsonify({'message': 'Trim added successfully'}), 201

# Delete a trim
@app.route('/api/trims/<string:trim_name>', methods=['DELETE'])
def delete_trim(trim_name):
    trim = Trim.query.filter_by(name=trim_name).first()
    if not trim:
        return jsonify({'error': 'Trim not found'}), 404
    db.session.delete(trim)
    db.session.commit()
    return jsonify({'message': 'Trim deleted successfully'})

# Update a trim
@app.route('/api/trims/<string:trim_name>', methods=['PUT'])
def update_trim(trim_name):
    trim = Trim.query.filter_by(name=trim_name).first()
    if not trim:
        return jsonify({'error': 'Trim not found'}), 404

    data = request.json
    trim.image = data.get('image', trim.image)
    trim.composition = data.get('composition', trim.composition)
    trim.structure = data.get('structure', trim.structure)
    trim.shade = data.get('shade', trim.shade)
    trim.brand = data.get('brand', trim.brand)
    trim.code = data.get('code', trim.code)

    db.session.commit()
    return jsonify({'message': 'Trim updated successfully'})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


### ✅ POST API to Add a Trim Variant
@app.route('/api/trims/<trim_id>/variants', methods=['POST'])
def add_trim_variant(trim_id):
    trim = Trim.query.get(trim_id)
    if not trim:
        return jsonify({"error": "Trim not found"}), 404

    data = request.json
    image = data.get("image")
    composition = data.get("composition")
    structure = data.get("structure")
    shade = data.get("shade")
    brand = data.get("brand")
    code = data.get("code")


    if not image or not composition or not structure or not shade or not brand:
        return jsonify({"error": "All fields are required"}), 400

    new_variant = TrimVariant(
        trim_id=trim.id,
        image=image,
        composition=composition,
        structure=structure,
        shade=shade,
        brand=brand,
        code = code
    )

    db.session.add(new_variant)
    db.session.commit()

    return jsonify({"message": "Trim variant added successfully", "id": new_variant.id})

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


if __name__ == '__main__':
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])
    app.run(debug=True)
