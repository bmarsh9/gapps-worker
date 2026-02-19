from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from jsonschema import validate
from croniter import croniter, CroniterBadCronError
from config import Config
import requests



Base = declarative_base()


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    schema = Column(JSON, default={})  # JSONSchema

    deployments = relationship(
        "Deployment", backref="integration", cascade="all, delete-orphan"
    )

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        return data

    def validate_config(self, config: dict):
        validate(instance=config, schema=self.schema)

    def create_deployment(
        self,
        config: dict,
        schedule: str = None,
        queue: str = "default",
        timeout: int = 3600,
    ):
        self.validate_config(config)

        if schedule:
            try:
                croniter(schedule)
            except CroniterBadCronError:
                raise ValueError("Invalid cron expression for schedule")

        return Deployment(
            integration_id=self.id,
            config=config,
            schedule=schedule,
            timeout=timeout,
            queue=queue,
            status="scheduled",
        )

    @staticmethod
    def pull_integrations():
        print(3)
        resp = requests.get(Config.GITHUB_RAW_URL, timeout=5)
        resp.raise_for_status()
        integrations = [i for i in resp.json() if i.get("enabled")]

        pulled_at = datetime.utcnow().isoformat()

        for integration in integrations:
            integration["version"] = pulled_at

        return integrations


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True)

    config = Column(JSON, default={})
    enabled = Column(Boolean, default=True)
    schedule = Column(String)  # cron -> "0/1 * * * *"
    timeout = Column(Integer, default=3600)
    version = Column(Integer, default=1)
    status = Column(String, default="scheduled")
    queue = Column(String, default="default")

    last_scheduled_at = Column(DateTime, nullable=True)

    jobs = relationship(
        "Job",
        backref="deployment",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    integration_id = Column(
        Integer, ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False
    )

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if self.last_scheduled_at:
            data["last_scheduled_at"] = self.last_scheduled_at.isoformat()
        data["integration_name"] = self.integration.name if self.integration else None
        return data

    def create_job(self):
        self.last_scheduled_at = datetime.utcnow()
        return Job(
            deployment_id=self.id,
            status="queued",
        )

    def list_violations(self):
        jobs = sorted(
            self.jobs,
            key=lambda j: j.finished_at or j.created_at or datetime.min,
            reverse=True
        )

        return [
            {
                "job_id": job.id,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                "violations": [v.as_dict() for v in job.violations]
            }
            for job in jobs
        ]


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    status = Column(String, default="queued")  # queued, in-progress, done, error
    result = Column(JSON, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    deployment_id = Column(
        Integer,
        ForeignKey("deployments.id", ondelete="CASCADE"),
        nullable=False
    )

    @property
    def queue(self):
        return self.deployment.queue if self.deployment else "default"

    @property
    def queue_seconds(self):
        if self.created_at and self.started_at:
            return int((self.started_at - self.created_at).total_seconds())
        return None

    @property
    def execution_seconds(self):
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds())
        return None

    @property
    def duration_seconds(self):
        if self.created_at and self.finished_at:
            return int((self.finished_at - self.created_at).total_seconds())
        return None

    def as_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["integration_name"] = self.deployment.integration.name
        data["config"] = self.deployment.config
        data["queue"] = self.queue
        data["duration_in_queue"] = self.queue_seconds
        data["duration_in_execution"] = self.execution_seconds
        data["duration_total"] = self.duration_seconds
        return data

    def create_violation(
        self,
        task_name: str,
        control_references: list,
        output: dict,
        severity: str = "medium",
        description: str = None,
        violation_type: str = None,
        environment: str = None,
        meta: dict = None,
        timestamp: datetime = None
    ):
        """
        Create and return a Violation tied to this Job.

        Required:
            - task_name: the task that triggered the violation
            - control_references: list of control dicts (id, framework, etc.)
            - output: the task output that caused the violation
        """

        violation = Violation(
            job_id=self.id,
            task_name=task_name,
            control_references=control_references,
            output=output,
            severity=severity,
            description=description,
            violation_type=violation_type,
            environment=environment,
            meta=meta or {},
            timestamp=timestamp or datetime.utcnow()
        )
        return violation

class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    task_name = Column(String, nullable=False)
    control_references = Column(JSON, nullable=False)  # List of controls (id, framework, etc.)
    output = Column(JSON, nullable=False)              # Task result that caused violation

    severity = Column(String, default="medium")        # Optional: low, medium, high, critical
    description = Column(Text, nullable=True)          # Optional: human-readable explanation
    violation_type = Column(String, nullable=True)     # Optional: e.g., misconfiguration
    environment = Column(String, nullable=True)        # Optional: env like 'prod'
    meta = Column(JSON, default={})                # Optional: extra context
    timestamp = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", backref="violations")

    def as_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "integration_name": self.integration_name,
            "task_name": self.task_name,
            "control_references": self.control_references,
            "output": self.output,
            "severity": self.severity,
            "description": self.description,
            "violation_type": self.violation_type,
            "environment": self.environment,
            "meta": self.meta,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @property
    def integration_name(self):
        if self.job and self.job.deployment and self.job.deployment.integration:
            return self.job.deployment.integration.name
        return None