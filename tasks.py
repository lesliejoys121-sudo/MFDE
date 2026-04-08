from typing import List, Dict

TASKS: Dict[str, Dict] = {
    "easy": {
        "description": "Clear signals, minimal noise, straightforward triage.",
        "steps_limit": 5,
        "reward_noise_prob": 0.0,
        "emails": [
            {
                "email_text": "Hi, I am stuck and need help resetting my password. Can you assist?",
                "sender": "user123@example.com",
                "subject": "Password Reset Help",
                "correct_decision": "reply",
                "correct_priority": "medium"
            },
            {
                "email_text": "Buy one get one free! Click here to win a trillion dollars now!!!",
                "sender": "spam@malicious.com",
                "subject": "URGENT WINNER",
                "correct_decision": "ignore",
                "correct_priority": "low"
            },
            {
                "email_text": "The server in building 4 is down. Multiple users reporting issues.",
                "sender": "monitoring@company.com",
                "subject": "CRITICAL: Server Down",
                "correct_decision": "escalate",
                "correct_priority": "high"
            },
            {
                "email_text": "Just wanted to say thanks for the help yesterday!",
                "sender": "client@partner.com",
                "subject": "Thank you",
                "correct_decision": "ignore",
                "correct_priority": "low"
            },
            {
                "email_text": "Can we schedule a meeting next Tuesday for the project review?",
                "sender": "manager@company.com",
                "subject": "Meeting Request",
                "correct_decision": "reply",
                "correct_priority": "medium"
            }
        ]
    },
    "medium": {
        "description": "Some misleading emails (fake urgency), ~30% reward noise.",
        "steps_limit": 7,
        "reward_noise_prob": 0.3,
        "emails": [
            {
                "email_text": "Hey, this is the CEO. I'm in a meeting and need you to buy 50 Apple gift cards for a client. HURRY!",
                "sender": "ceo.urgent.office@gmail.com",
                "subject": "URGENT REQUEST FROM CEO",
                "correct_decision": "ignore",
                "correct_priority": "low"
            },
            {
                "email_text": "Invoice #8849 is past due. Please review the attached document.",
                "sender": "billing@vendor-system.com",
                "subject": "Overdue Invoice",
                "correct_decision": "reply",
                "correct_priority": "medium"
            },
            {
                "email_text": "I noticed a strange login from an unknown IP address. Please verify your account.",
                "sender": "security-alert@company-platform.com",
                "subject": "Security Alert",
                "correct_decision": "escalate",
                "correct_priority": "high"
            },
            {
                "email_text": "Your subscription will expire in 3 days. Renew now to avoid interruption.",
                "sender": "no-reply@service.com",
                "subject": "Subscription Renewal",
                "correct_decision": "reply",
                "correct_priority": "medium"
            },
            {
                "email_text": "Great news! Your package has been delivered. Click here to track.",
                "sender": "shipping@delivery-service.com",
                "subject": "Package Delivered",
                "correct_decision": "ignore",
                "correct_priority": "low"
            },
            {
                "email_text": "I found a bug in the production API. It allows unauthorized access.",
                "sender": "whitehat@security.org",
                "subject": "Responsible Disclosure: Security vulnerability",
                "correct_decision": "escalate",
                "correct_priority": "high"
            },
            {
                "email_text": "Can you review these documents before our call in 10 minutes?",
                "sender": "colleague@company.com",
                "subject": "Quick review",
                "correct_decision": "reply",
                "correct_priority": "medium"
            }
        ]
    },
    "hard": {
        "description": "Highly deceptive emails, ambiguous content, strong misleading reward noise (~50%).",
        "steps_limit": 10,
        "reward_noise_prob": 0.5,
        "emails": [
            {
                "email_text": "Emergency! The main database just crashed. Everything is gone. Come to the office now!",
                "sender": "it-support-urgent@unknown-provider.net",
                "subject": "DATABASE WIPE - EMERGENCY",
                "correct_decision": "ignore",
                "correct_priority": "low"
            },
            {
                "email_text": "We've detected a significant drop in user engagement following the latest update.",
                "sender": "analytics@company.com",
                "subject": "Engagement Report",
                "correct_decision": "reply",
                "correct_priority": "medium"
            },
            {
                "email_text": "Regarding our conversation about the merger. I need the final documents immediately.",
                "sender": "partner-v-merger@legal-firm-abc.com",
                "subject": "Merger Documents",
                "correct_decision": "escalate",
                "correct_priority": "high"
            },
            {
                "email_text": "Looking for talented engineers like you! Check out our open positions.",
                "sender": "recruiter@another-company.com",
                "subject": "Join our team",
                "correct_decision": "ignore",
                "correct_priority": "low"
            },
            {
                "email_text": "I can't access my email. It says my account is locked.",
                "sender": "frustrated-user@company.com",
                "subject": "Account Locked",
                "correct_decision": "reply",
                "correct_priority": "medium"
            },
            {
                "email_text": "The payroll system has a major error and employees aren't being paid.",
                "sender": "hr-ops@company.com",
                "subject": "Payroll Issue",
                "correct_decision": "escalate",
                "correct_priority": "high"
            },
            {
                "email_text": "Final notice regarding your account balance. Action required.",
                "sender": "collections@debt-collector.com",
                "subject": "Final Notice",
                "correct_decision": "ignore",
                "correct_priority": "low"
            },
            {
                "email_text": "I'll be out of the office starting tomorrow. Please contact John for any issues.",
                "sender": "teammate@company.com",
                "subject": "OOO Notice",
                "correct_decision": "ignore",
                "correct_priority": "low",
                "reason": "Informational email requiring no action."
            },
            {
                "email_text": "Your password is set to expire in 48 hours. Update it now.",
                "sender": "it-dept@company.com",
                "subject": "Password Expiry Notice",
                "correct_decision": "reply",
                "correct_priority": "medium",
                "reason": "Standard IT security policy reminder."
            },
            {
                "email_text": "We are being sued by a competitor for patent infringement.",
                "sender": "legal-council@company.com",
                "subject": "Legal Action: Patent Infringement",
                "correct_decision": "escalate",
                "correct_priority": "high",
                "reason": "Major legal threat requiring immediate escalation."
            }
        ]
    }
}
