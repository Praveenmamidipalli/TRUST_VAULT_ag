from typing import Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from app.models.enums import DocumentCategory

# Supervised training samples across enterprise document domains
TRAINING_DATA = [
    # LEGAL
    ("This Non-Disclosure Agreement (NDA) and confidential settlement terms are binding between parties.", DocumentCategory.LEGAL),
    ("Master Services Agreement, arbitration clause, liabilities, indemnification and jurisdiction of courts.", DocumentCategory.LEGAL),
    ("Contractual obligations, terms of service, privacy policy and copyright trademark infringement clauses.", DocumentCategory.LEGAL),
    ("Intellectual property assignment, warranty disclaimer, mutual non-disclosure and governing state laws.", DocumentCategory.LEGAL),
    
    # FINANCIAL
    ("Quarterly financial report, balance sheet, profit and loss, EBITDA margin and revenue forecast for Q3.", DocumentCategory.FINANCIAL),
    ("Audited statements, taxation liabilities, capital expenditures, equity dilution and dividend payout.", DocumentCategory.FINANCIAL),
    ("Invoicing guidelines, Accounts Payable, ledger reconciliation, gross profit, cash flow statements.", DocumentCategory.FINANCIAL),
    ("Budget allocation for fiscal year 2026, operational cost reduction and shareholder annual earnings.", DocumentCategory.FINANCIAL),
    
    # HR
    ("Employee handbook, PTO vacation policies, health insurance benefits and onboarding checklist.", DocumentCategory.HR),
    ("Performance appraisal review, compensation band, annual bonus eligibility and parental leave guidelines.", DocumentCategory.HR),
    ("Code of conduct, anti-harassment policy, termination procedure and workplace safety protocols.", DocumentCategory.HR),
    ("Talent acquisition, recruitment pipeline, offer letter template and employee relocation assistance.", DocumentCategory.HR),
    
    # TECHNICAL
    ("System architecture diagram, microservices API gateway, PostgreSQL indexing and Kubernetes deployments.", DocumentCategory.TECHNICAL),
    ("FastAPI backend specifications, JWT authentication implementation, CI/CD pipeline and Docker compose setup.", DocumentCategory.TECHNICAL),
    ("Software requirements specification, database schema migrations, latency benchmarks and unit test coverage.", DocumentCategory.TECHNICAL),
    ("Encryption algorithms, Argon2 password hashing, SSL TLS certificates and network firewall routing.", DocumentCategory.TECHNICAL),
    
    # GENERAL
    ("Company all-hands meeting agenda, executive town hall announcements and quarterly milestone celebration.", DocumentCategory.GENERAL),
    ("Internal team lunch logistics, office supplies inventory and holiday calendar notice.", DocumentCategory.GENERAL),
    ("Welcome message to our new project team members and weekly meeting minutes summary.", DocumentCategory.GENERAL),
    ("General operational update, parking guidelines and building access keycard distribution.", DocumentCategory.GENERAL),
]


class DocumentClassifier:
    """Supervised ML model for automatic document domain classification.
    
    Security Invariant:
    - AI classification is purely advisory.
    - Classification suggestions NEVER alter access control policies or document permissions.
    """

    def __init__(self):
        texts = [sample[0] for sample in TRAINING_DATA]
        labels = [sample[1].value for sample in TRAINING_DATA]

        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(stop_words="english", sublinear_tf=True)),
            ("clf", MultinomialNB(alpha=0.5))
        ])
        self.pipeline.fit(texts, labels)

    def predict_category(self, text: str) -> Tuple[DocumentCategory, float]:
        """Predicts the most probable category and returns (category, confidence_score)."""
        if not text or len(text.strip()) < 10:
            return DocumentCategory.GENERAL, 0.50

        probs = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_
        top_idx = probs.argmax()

        pred_label = classes[top_idx]
        confidence = float(probs[top_idx])

        return DocumentCategory(pred_label), round(confidence, 2)


document_classifier = DocumentClassifier()
