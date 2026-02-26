from flask import Flask, request, jsonify, abort
from db import db_session, init_db
from models import Integration, Deployment, Job, Violation
from sqlalchemy import desc
import logging
from datetime import datetime
from jsonschema import ValidationError
from utils.decorators import require_token


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
init_db()

# -------------------------
# Integration Endpoints
# -------------------------

@app.route("/init-integrations", methods=["POST"])
@require_token
def init_integrations():
    try:
        integrations = Integration.pull_integrations()
    except Exception as e:
        logger.error(f"Failed to pull integrations from GitHub: {e}")
        return jsonify({"error": "Failed to fetch integrations from GitHub"}), 502

    created = []
    updated = []

    for data in integrations:
        existing = db_session.query(Integration).filter_by(name=data["name"]).first()

        if not existing:
            integration = Integration(
                name=data["name"],
                title=data.get("title", data["name"]),
                description=data.get("description"),
                schema=data.get("schema", {}),
                schedule=data.get("schedule"),
                is_service=data.get("is_service")
            )
            db_session.add(integration)
            created.append(data["name"])
        else:
            changed = False
            for field in ["title", "description", "schema", "schedule"]:
                if data.get(field) and getattr(existing, field) != data.get(field):
                    setattr(existing, field, data.get(field))
                    changed = True
            if changed:
                updated.append(data["name"])

    db_session.commit()
    return jsonify({"created": created, "updated": updated}), 200


@app.route("/integrations", methods=["DELETE"])
@require_token
def delete_all_integrations():
    try:
        integrations = db_session.query(Integration).all()
        for i in integrations:
            db_session.delete(i)
        db_session.commit()
        return jsonify({"message": "All integrations deleted"}), 200
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/integrations", methods=["GET"])
@require_token
def list_integrations():
    integrations = db_session.query(Integration).all()
    return jsonify([i.as_dict() for i in integrations])


@app.route("/integrations/<string:id>", methods=["GET"])
@require_token
def get_integration(id):
    integration = db_session.query(Integration).filter(Integration.id == id).first()
    if not integration:
        return jsonify({"error": "Integration not found"}), 404
    return jsonify(integration.as_dict())


@app.route("/integrations", methods=["POST"])
@require_token
def create_integration():
    data = request.json
    required = ["name", "schema"]
    if not all(k in data for k in required):
        abort(400, "Missing required fields: 'name' and 'schema'")

    if db_session.query(Integration).filter_by(name=data["name"]).first():
        return jsonify({"error": "Integration with that name already exists"}), 400

    integration = Integration(
        name=data["name"],
        title=data.get("title", data["name"]),
        description=data.get(
            "description", f"Integration:{data['name']} does not have a description"
        ),
        schema=data["schema"],
        schedule=data.get("schedule"),
        is_service=data.get("is_service")
    )
    db_session.add(integration)
    db_session.commit()
    return jsonify({"id": integration.id}), 201


# -------------------------
# Deployment Endpoints
# -------------------------

@app.route("/tenants/<string:tenant_id>/deployments", methods=["POST"])
@require_token
def create_deployment(tenant_id):
    data = request.get_json()
    if not all(k in data for k in ["integration_id", "config"]):
        abort(400, "Missing required fields")
    integration = db_session.get(Integration, data["integration_id"])
    if not integration:
        abort(404, "Integration not found")

    try:
        deployment = integration.create_deployment(
            config=data["config"],
            schedule=data.get("schedule"),
            queue=data.get("queue"),
            timeout=data.get("timeout", 3600),
            tenant_id=tenant_id
        )
        db_session.add(deployment)
        db_session.commit()
        return jsonify({"deployment_id": deployment.id}), 201
    except ValidationError as e:
        return jsonify({"error": f"Invalid config: {e.message}"}), 400
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 400


@app.route("/tenants/<string:tenant_id>/deployments/<string:deployment_id>", methods=["PUT"])
@require_token
def update_deployment(tenant_id, deployment_id):
    data = request.get_json()
    deployment = db_session.query(Deployment).filter_by(
        id=deployment_id, tenant_id=tenant_id
    ).first()

    if not deployment:
        return jsonify({"error": "Deployment not found"}), 404

    if "config" in data:
        deployment.config = data["config"]
    if "enabled" in data:
        deployment.enabled = data["enabled"]
    if "schedule" in data:
        deployment.schedule = data["schedule"]
    if "queue" in data:
        deployment.queue = data["queue"]
    if "timeout" in data:
        deployment.timeout = data["timeout"]

    try:
        db_session.commit()
        return jsonify(deployment.as_dict())
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/tenants/<string:tenant_id>/deployments", methods=["GET"])
@require_token
def list_deployments(tenant_id):
    deployments = db_session.query(Deployment).filter_by(tenant_id=tenant_id).all()
    return jsonify([i.as_dict() for i in deployments])


@app.route("/tenants/<string:tenant_id>/deployments/<string:id>", methods=["GET"])
@require_token
def get_deployment(tenant_id, id):
    deployment = db_session.query(Deployment).filter_by(
        id=id, tenant_id=tenant_id
    ).first()
    if not deployment:
        return jsonify({"error": "Deployment not found"}), 404
    return jsonify(deployment.as_dict())


@app.route("/tenants/<string:tenant_id>/deployments/<string:id>", methods=["DELETE"])
@require_token
def delete_deployment(tenant_id, id):
    deployment = db_session.query(Deployment).filter_by(
        id=id, tenant_id=tenant_id
    ).first()
    if not deployment:
        return jsonify({"error": "Deployment not found"}), 404
    db_session.delete(deployment)
    db_session.commit()
    return jsonify({"message": "ok"})


@app.route("/tenants/<string:tenant_id>/deployments/<string:id>/violations", methods=["GET"])
@require_token
def list_violations_for_deployment(tenant_id, id):
    deployment = db_session.query(Deployment).filter_by(
        id=id, tenant_id=tenant_id
    ).first()
    if not deployment:
        return jsonify([])
    return jsonify(deployment.list_violations())


# -------------------------
# Job Endpoints
# -------------------------

@app.route("/tenants/<string:tenant_id>/jobs", methods=["GET"])
@require_token
def list_jobs(tenant_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    before = request.args.get('before', None)
    after = request.args.get('after', None)
    deployment_id = request.args.get('deployment_id', None)

    per_page = min(per_page, 100)

    query = (
        db_session.query(Job)
        .join(Job.deployment)
        .filter(Deployment.tenant_id == tenant_id)
    )

    if before:
        query = query.filter(Job.finished_at <= datetime.fromisoformat(before))
    if after:
        query = query.filter(Job.finished_at >= datetime.fromisoformat(after))
    if deployment_id:
        query = query.filter(Job.deployment_id == deployment_id)

    total_jobs = query.count()
    offset = (page - 1) * per_page

    jobs = (
        query
        .order_by(Job.created_at.desc())
        .limit(per_page)
        .offset(offset)
        .all()
    )

    return jsonify({
        'jobs': [i.as_dict() for i in jobs],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_jobs,
            'pages': (total_jobs + per_page - 1) // per_page
        }
    })


@app.route("/tenants/<string:tenant_id>/jobs/<string:job_id>", methods=["GET"])
@require_token
def get_job(tenant_id, job_id):
    job = (
        db_session.query(Job)
        .join(Job.deployment)
        .filter(Job.id == job_id, Deployment.tenant_id == tenant_id)
        .first()
    )
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job.as_dict())


# -------------------------
# Violation Endpoints
# -------------------------

@app.route("/tenants/<string:tenant_id>/violations", methods=["GET"])
@require_token
def list_violations(tenant_id):
    violations = (
        db_session.query(Violation)
        .join(Violation.job)
        .join(Job.deployment)
        .filter(Deployment.tenant_id == tenant_id)
        .all()
    )
    return jsonify([i.as_dict() for i in violations])


# -------------------------
# Internal / Worker Endpoints (no tenant scope)
# -------------------------

@app.route("/api/deployments/scheduled", methods=["GET"])
def get_scheduled_deployments():
    deployments = db_session.query(Deployment).filter(
        Deployment.enabled == True, Deployment.schedule != None
    ).all()
    return jsonify([d.as_dict() for d in deployments])


@app.route("/jobs", methods=["POST"])
def create_job():
    data = request.json
    if not data.get("deployment_id"):
        abort(400, "deployment_id is required")
    deployment = db_session.get(Deployment, data["deployment_id"])
    if not deployment:
        abort(404, "Deployment not found")
    job = deployment.create_job()
    db_session.add(job)
    db_session.commit()
    return jsonify({"id": job.id}), 201


@app.route("/jobs/<int:job_id>", methods=["GET"])
def get_job_internal(job_id):
    job = db_session.get(Job, job_id)
    if job:
        return jsonify(job.as_dict())
    return jsonify({"error": "Job not found"}), 404


@app.route("/jobs/next", methods=["GET"])
def get_next_job():
    queue = request.args.get("queue", "default")
    session = db_session()
    try:
        job = (
            session.query(Job)
            .join(Job.deployment)
            .filter(Job.status == "queued")
            .filter(Deployment.queue == queue)
            .with_for_update(skip_locked=True)
            .first()
        )
        if job:
            job.status = "in-progress"
            job.started_at = datetime.utcnow()
            session.commit()
            return jsonify(job.as_dict()), 200
        return jsonify({"message": "No jobs available"}), 204
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@app.route("/jobs/<int:job_id>/complete", methods=["POST"])
def complete_job(job_id):
    data = request.json
    db_session.query(Job).filter(Job.id == job_id).update({
        Job.status: data.get("status", "done"),
        Job.result: data.get("result", {}),
        Job.finished_at: datetime.utcnow()
    })
    db_session.commit()
    return jsonify({"message": "updated"}), 200


@app.route("/jobs/<string:job_id>/violations", methods=["POST"])
def create_violation(job_id):
    data = request.get_json()
    job = db_session.get(Job, job_id)
    if "timestamp" in data and isinstance(data["timestamp"], str):
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
    violation = job.create_violation(**data)
    db_session.add(violation)
    db_session.commit()
    return jsonify({"message": "ok"})


@app.route("/jobs", methods=["DELETE"])
def delete_jobs():
    before = request.args.get('before', None)
    after = request.args.get('after', None)
    if not before and not after:
        return jsonify({"error": "At least one of 'before' or 'after' is required"}), 400
    query = db_session.query(Job)
    if before:
        query = query.filter(Job.finished_at <= datetime.fromisoformat(before))
    if after:
        query = query.filter(Job.finished_at >= datetime.fromisoformat(after))
    try:
        count = query.count()
        query.delete()
        db_session.commit()
        return jsonify({"deleted": count}), 200
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/projects/<string:project_id>/deployments', methods=['POST'])
def add_project_to_deployments(project_id):
    data = request.get_json()
    if not data or 'deployment_ids' not in data:
        return jsonify({'message': 'deployment_ids is required'}), 400

    deployment_ids = [int(i) for i in data['deployment_ids']]
    deployments = db_session.query(Deployment).filter(Deployment.id.in_(deployment_ids)).all()

    if len(deployments) != len(deployment_ids):
        found = {d.id for d in deployments}
        missing = [i for i in deployment_ids if i not in found]
        return jsonify({'message': f'Deployments not found: {missing}'}), 404

    added, skipped = [], []
    for deployment in deployments:
        existing = set(deployment.get_project_ids())
        if project_id in existing:
            skipped.append(deployment.id)
        else:
            deployment.add_project_id(project_id)
            added.append(deployment.id)

    db_session.commit()
    return jsonify({
        'added':   added,
        'skipped': skipped,
        'message': f'Project {project_id} added to {len(added)} deployment(s), {len(skipped)} already linked'
    }), 200


@app.route('/projects/<string:project_id>/deployments', methods=['DELETE'])
def remove_project_from_deployments(project_id):
    data = request.get_json()
    if not data or 'deployment_ids' not in data:
        return jsonify({'message': 'deployment_ids is required'}), 400

    deployment_ids = [int(i) for i in data['deployment_ids']]
    deployments = db_session.query(Deployment).filter(Deployment.id.in_(deployment_ids)).all()

    removed = []
    for deployment in deployments:
        deployment.remove_project_id(project_id)
        removed.append(deployment.id)

    db_session.commit()
    return jsonify({
        'removed': removed,
        'message': f'Project {project_id} removed from {len(removed)} deployment(s)'
    }), 200

# -------------------------
# Cleanup
# -------------------------
@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()
