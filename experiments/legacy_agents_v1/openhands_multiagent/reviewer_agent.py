"""
Reviewer Agent - Κάνει code review, architecture review και best practices check
"""

from pr_review_expert import pr_expert
from logger import log

class ReviewerAgent:
    def review_code(self, code_or_pr: str):
        log.info("Reviewer Agent: Performing code review")
        review = pr_expert.review_pr(code_or_pr)
        return review

# Register
reviewer = ReviewerAgent()