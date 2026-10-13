from django.db import models
from django.db.models import CASCADE

# ------------------------------------------------------------
# Position Choices
# ------------------------------------------------------------

POSITION_CHOICES = [
    ("QB", "Quarterback"),
    ("RB", "Running Back"),
    ("WR", "Wide Receiver"),
    ("TE", "Tight End"),
    ("DST", "Defense/Special Teams"),
    ("FLEX", "Flex"),
]


# ------------------------------------------------------------
# Player Model (Main DFS Player Table)
# ------------------------------------------------------------

class Player(models.Model):
    # DraftKings ID (optional, not unique)
    dk_id = models.CharField(max_length=50, null=True, blank=True)

    # Core fields
    name = models.CharField(max_length=100, unique=True)
    position = models.CharField(max_length=10, choices=POSITION_CHOICES)
    team = models.CharField(max_length=10, null=True, blank=True)
    opponent = models.CharField(max_length=10, null=True, blank=True)

    salary = models.IntegerField(default=0)
    projection = models.FloatField(default=0.0)

    # DK fields your views expect
    ownership = models.FloatField(null=True, blank=True)
    game = models.CharField(max_length=50, null=True, blank=True)
    week = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.position})"


# ------------------------------------------------------------
# Serialized Lineups (Training Data for Neural Network)
# ------------------------------------------------------------

class SerializedEntry(models.Model):
    ENTRY_TYPES = [
        ("WIN", "Winning"),
        ("LOSS", "Losing"),
        ("GEN", "Generated"),
    ]

    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    position = models.CharField(max_length=10, choices=POSITION_CHOICES)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.entry_type} - {self.position}"


# ------------------------------------------------------------
# Week-by-Week Player Performance
# ------------------------------------------------------------

class WeekPerformance(models.Model):
    player = models.ForeignKey(Player, related_name='week_performances', on_delete=models.CASCADE)
    week = models.IntegerField(null=True, blank=True)
    points = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['week']

    def __str__(self):
        return f"{self.player.name} - Week {self.week}: {self.points}"




# ------------------------------------------------------------
# Sports Reflection (Your custom content model)
# ------------------------------------------------------------

class Sports(models.Model):
    topic = models.CharField(max_length=100)
    reference = models.CharField(max_length=100)
    reflection = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.topic


# ------------------------------------------------------------
# Sports News (Your custom news model)
# ------------------------------------------------------------

class SportsNews(models.Model):
    topic = models.CharField(max_length=100)
    reference = models.CharField(max_length=100)
    news = models.TextField()

    def __str__(self):
        return self.topic


# ------------------------------------------------------------
# DK Salary File Uploads
# ------------------------------------------------------------

class DKSalaryFile(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to="dk_files/")

    def __str__(self):
        return f"DK Salaries ({self.uploaded_at:%Y-%m-%d})"


# ------------------------------------------------------------
# Full Lineup Storage
# ------------------------------------------------------------

class FullLineup(models.Model):
    qb = models.JSONField()
    rb1 = models.JSONField()
    rb2 = models.JSONField()
    wr1 = models.JSONField()
    wr2 = models.JSONField()
    wr3 = models.JSONField()
    te = models.JSONField()
    flex = models.JSONField()
    dst = models.JSONField()

    total_salary = models.IntegerField()
    total_projection = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lineup {self.id} - {self.total_projection} proj"


class LosingLineup(models.Model):
    lineup = models.JSONField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SavedLineup(models.Model):
    data = models.JSONField()
    result = models.CharField(max_length=10, default="AI")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.result} lineup saved at {self.created_at}"


class WinningLineup(models.Model):
    lineup = models.JSONField()
    score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)


# ------------------------------------------------------------
# User Profiles
# ------------------------------------------------------------

class UserProfile(models.Model):
    dsflineups_name067 = models.CharField(max_length=100)
    dfslineups_password020 = models.CharField(max_length=100)
    logged_in756 = models.DateTimeField(auto_now_add=True)


class DFSLineup(models.Model):
    owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    data = models.JSONField()
