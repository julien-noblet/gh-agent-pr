from laya import Router

router = Router()  # downloads a checkpoint on first use; Router(preload=True) loads all three up front

state = "Hi, we were billed twice for March. Please refund the duplicate today or we will cancel our plan."
questions = {
    "department": {"type": "choice", "instructions": "Which department should handle this?",
                   "criteria": {"billing": "invoices, payments, refunds",
                                "technical": "bugs, outages, system errors",
                                "other": "everything else"}},
    "urgency": {"type": "score", "instructions": "How urgent is this?",
                "criteria": ["not urgent", "soon", "blocking"]},
    "churn_risk": {"type": "noul", "instructions": "Does the user threaten to cancel or leave?"},
}

requests = [
    {"state": "Please refund invoice 1", "questions": questions},
    {"state": "تم خصم المبلغ مرتين", "questions": questions},
    {"state": "Please refund invoice 2", "questions": questions},
]

results = Router(max_loaded=1).predict_batch(requests)
for r in results:
    print(r["answers"]["department"]["choice"])  # billing
    print(r["answers"]["churn_risk"]["noul"])    # probability the answer is yes
    print(r["routing"]["model"])                 # english
    print("---")