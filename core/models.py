from django.db import models

class GovernmentOpportunity(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    required_workers = models.IntegerField()
    closing_date = models.DateField()
    category = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class GovernmentApplication(models.Model):
    """Tracks which worker applied for which government opportunity."""
    opportunity = models.ForeignKey(GovernmentOpportunity, on_delete=models.CASCADE, related_name='applications')
    worker = models.ForeignKey('workers.WorkerProfile', on_delete=models.CASCADE, related_name='gov_applications')
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')],
        default='pending'
    )
    cover_letter = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('opportunity', 'worker') # A worker can apply only once per project

    def __str__(self):
        return f"{self.worker} applied for {self.opportunity.title}"
