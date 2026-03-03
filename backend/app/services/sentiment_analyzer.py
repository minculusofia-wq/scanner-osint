from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class SentimentAnalyzer:
    """VADER-based sentiment analysis optimized for news/social text."""

    def __init__(self):
        self._vader = SentimentIntensityAnalyzer()

    def score_item(self, title: str, summary: str = "") -> float:
        """Compute sentiment score for an intelligence item.

        Returns float in [-1, +1].
        Weighted: title * 0.6 + summary * 0.4.
        """
        title_score = self._vader.polarity_scores(title)["compound"]
        if summary:
            summary_score = self._vader.polarity_scores(summary)["compound"]
            return title_score * 0.6 + summary_score * 0.4
        return title_score
