"""
Machine Learning Pro Skill.

Πραγματικό πλέον: παράγει concrete ML προτάσεις + εκτελέσιμο pipeline code μέσω
του μοντέλου, με έμφαση στο market/trading domain του project (features από
indicators, walk-forward backtesting, leakage avoidance).
"""

from openhands_skills.expert_base import ExpertSkill


class MachineLearningPro(ExpertSkill):
    ROLE = "ml"
    EXPERTISE = (
        "a senior ML engineer specialised in quantitative/financial ML "
        "(feature engineering from market indicators, gradient boosting, proper "
        "time-series validation, avoiding look-ahead bias)"
    )

    def suggest_ml_improvement(self, task: str = "", context: dict = None) -> str:
        t = (
            "Analyse the described project/dataset and propose concrete, "
            "prioritised ML improvements: features to add, models to try, "
            "validation scheme, and metrics. Warn about data leakage and "
            f"overfitting risks specific to this case.\n\n{task or 'the trading signal project'}"
        )
        return self.consult(t, context, max_tokens=4000)

    def create_ml_pipeline(self, task: str, context: dict = None) -> str:
        t = (
            "Write a runnable Python ML pipeline for the following task: data "
            "loading, feature engineering, train/validation split with "
            "walk-forward (time-series safe), model training, backtesting and "
            f"evaluation. Return complete code.\n\nTask: {task}"
        )
        return self.consult(t, context, max_tokens=6000)


# Register
ml_pro = MachineLearningPro()
