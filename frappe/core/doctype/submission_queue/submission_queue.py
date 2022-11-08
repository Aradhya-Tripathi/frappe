# Copyright (c) 2022, Frappe Technologies and contributors
# For license information, please see license.txt

from rq import get_current_job
from rq.job import Job
from rq.registry import FailedJobRegistry

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.model.document import Document
from frappe.monitor import add_data_to_monitor
from frappe.utils import now, time_diff_in_seconds
from frappe.utils.background_jobs import get_queue, get_redis_conn
from frappe.utils.data import cint


class SubmissionQueue(Document):
	@property
	def created_at(self):
		return self.creation

	@property
	def enqueued_by(self):
		return self.owner

	@property
	def queued_doc(self):
		return getattr(self, "to_be_queued_doc", frappe.get_doc(self.ref_doctype, self.ref_docname))

	@staticmethod
	def clear_old_logs(days=30):
		from frappe.query_builder import Interval
		from frappe.query_builder.functions import Now

		table = frappe.qb.DocType("Submission Queue")
		frappe.db.delete(table, filters=(table.modified < (Now() - Interval(days=days))))

	def insert(self, to_be_queued_doc: Document, action: str):
		self.to_be_queued_doc = to_be_queued_doc
		self.action_for_queuing = action
		super().insert(ignore_permissions=True)

	def lock(self):
		self.queued_doc.lock()

	def unlock(self):
		self.queued_doc.unlock()

	def after_insert(self):
		self.queue_action(
			"background_submission",
			to_be_queued_doc=self.queued_doc,
			action_for_queuing=self.action_for_queuing,
			timeout=600,
			enqueue_after_commit=True,
		)

	def background_submission(self, to_be_queued_doc: Document, action_for_queuing: str):
		current_job = get_current_job()

		# Set the job id for that submission doctype
		frappe.db.set_value(
			self.doctype,
			self.name,
			{"job_id": current_job.id},
			update_modified=False,
		)
		_action = action_for_queuing.lower()
		if _action == "update":
			_action = "submit"

		try:
			getattr(to_be_queued_doc, _action)()
			add_data_to_monitor(
				doctype=to_be_queued_doc.doctype,
				action=_action,
				execution_time=cint(time_diff_in_seconds(now(), self.created_at)),
				enqueued_by=self.enqueued_by,
			)
			values = {"status": "Finished"}
		except Exception:
			values = {"status": "Failed", "exception": frappe.get_traceback()}
			frappe.db.rollback()

		values["ended_at"] = now()
		frappe.db.set_value(self.doctype, self.name, values, update_modified=False)
		self.notify(values["status"], action_for_queuing)

	def notify(self, submission_status: str, action: str):
		if submission_status == "Failed":
			doctype = self.doctype
			docname = self.name
			message = _("Submission of {0} {1} with action {2} failed")
		else:
			doctype = self.ref_doctype
			docname = self.ref_docname
			message = _("Submission of {0} {1} with action {2} completed successfully")

		message = message.format(
			frappe.bold(str(self.ref_doctype)), frappe.bold(self.ref_docname), frappe.bold(action)
		)

		if cint(time_diff_in_seconds(now(), self.created_at)) <= 60:
			frappe.publish_realtime(
				"msgprint",
				{
					"message": message
					+ f". View it <a href='/app/{doctype.lower().replace(' ', '-')}/{docname}'><b>here</b></a>",
					"alert": True,
					"indicator": "red" if submission_status == "Failed" else "green",
				},
				user=self.enqueued_by,
			)
		else:
			notification_doc = {
				"type": "Alert",
				"document_type": doctype,
				"document_name": docname,
				"subject": message,
			}

			notify_to = frappe.db.get_value("User", self.enqueued_by, fieldname="email")
			enqueue_create_notification([notify_to], notification_doc)

	def _unlock_reference_doc(self):
		job_id = frappe.db.get_value(self.doctype, self.name, "job_id")
		if not job_id:
			# assuming the job failed here (?)
			status = "failed"

		queued_doc = self.queued_doc

		# Job finished successfully however action was never completed (?)
		if status == "finished" and queued_doc.docstatus == 0:
			status = "failed"

		# Checking if job is queue to be executed/executing
		if status in ("queued", "started"):
			frappe.msgprint(_("Document in queue for execution!"))

		# Checking any one of the possible termination statuses
		elif status in ("failed", "canceled", "stopped"):
			queued_doc.unlock()
			values = {"status": "Failed"}

			# Defining job exception when unlocking document.
			registry = FailedJobRegistry(queue=get_queue(qtype="default"))
			# If job id is None then this job won't exist in the failed registry
			for jid in registry.get_job_ids():
				if jid == job_id:
					job = Job.fetch(job_id, connection=get_redis_conn())
					values = {"status": "Failed", "exception": job.exc_info}

			frappe.db.set_value(self.doctype, self.name, values, update_modified=False)
			frappe.msgprint(_("Document Unlocked"))

	@frappe.whitelist()
	def unlock_doc(self):
		# NOTE: this can lead to some weird unlocking/locking behaviours.
		# for example: hitting unlock on a submission could lead to unlocking of another submission
		# of the same reference document.

		if self.status != "Queued":
			return

		self._unlock_reference_doc()


def queue_submission(doc: Document, action: str):
	queue = frappe.new_doc("Submission Queue")
	queue.state = "Queued"
	queue.ref_doctype = doc.doctype
	queue.ref_docname = doc.name
	queue.insert(doc, action)

	frappe.msgprint(
		_("Queued for Submission. You can track the progress over {0}.").format(
			f"<a href='/app/submission-queue/{queue.name}'><b>here</b></a>"
		),
		indicator="green",
		alert=True,
	)


@frappe.whitelist()
def get_latest_submissions(doctype, docname):
	# NOTE: not used creation as orderby intentianlly as we have used update_modified=False everywhere
	# hence assuming modified will be equal to creation for submission queue documents

	dt = "Submission Queue"
	filters = {"ref_doctype": doctype, "ref_docname": docname}
	return {
		"latest_submission": frappe.db.get_value(dt, filters),
		"latest_failed_submission": frappe.db.get_value(dt, filters.update({"status": "Failed"})),
	}