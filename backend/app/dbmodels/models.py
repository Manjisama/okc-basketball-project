# -*- coding: utf-8 -*-
"""Contains models related to stats"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Season(models.Model):
    """Season model for managing basketball seasons"""
    season_id = models.AutoField(primary_key=True)
    year_start = models.IntegerField(null=False)
    year_end = models.IntegerField(null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app.seasons'
        indexes = [
            models.Index(fields=['year_start', 'year_end']),
        ]

    def __str__(self):
        return f"{self.year_start}-{self.year_end}"


class Team(models.Model):
    """Team model for basketball teams"""
    team_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app.teams'
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class Game(models.Model):
    """Game model for basketball games"""
    game_id = models.AutoField(primary_key=True)
    date = models.DateField(null=False)
    season_id = models.ForeignKey(Season, on_delete=models.CASCADE, db_column='season_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app.games'
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['season_id']),
        ]

    def __str__(self):
        return f"Game {self.game_id} on {self.date}"


class GameTeam(models.Model):
    """GameTeam model for game-team relationships"""
    game_id = models.ForeignKey(Game, on_delete=models.CASCADE, db_column='game_id')
    team_id = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='team_id')
    is_home = models.BooleanField(null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app.game_teams'
        unique_together = [['game_id', 'team_id']]
        indexes = [
            models.Index(fields=['game_id']),
            models.Index(fields=['team_id']),
        ]

    def __str__(self):
        return f"{self.team_id} in Game {self.game_id} ({'Home' if self.is_home else 'Away'})"


class Player(models.Model):
    """Player model for basketball players"""
    player_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=False)
    team_id = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='team_id')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app.players'
        indexes = [
            models.Index(fields=['team_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class Action(models.Model):
    """Action model for basketball action types"""
    action_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True, null=False)
    name = models.CharField(max_length=100, null=False)

    class Meta:
        db_table = 'app.actions'
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return self.name


class Event(models.Model):
    """Event model for basketball game events"""
    EVENT_TYPE_CHOICES = [
        ('shot', 'Shot'),
        ('pass', 'Pass'),
        ('turnover', 'Turnover'),
    ]

    event_id = models.AutoField(primary_key=True)
    source_event_id = models.IntegerField(unique=True, null=False)
    player_id = models.ForeignKey(Player, on_delete=models.CASCADE, db_column='player_id')
    game_id = models.ForeignKey(Game, on_delete=models.CASCADE, db_column='game_id')
    team_id = models.ForeignKey(Team, on_delete=models.CASCADE, db_column='team_id', null=True, blank=True)
    action_id = models.ForeignKey(Action, on_delete=models.CASCADE, db_column='action_id')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    x_ft = models.FloatField(null=True, blank=True)
    y_ft = models.FloatField(null=True, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app.events'
        indexes = [
            models.Index(fields=['source_event_id']),
            models.Index(fields=['player_id']),
            models.Index(fields=['game_id']),
            models.Index(fields=['action_id', 'event_type']),
            models.Index(fields=['player_id', 'action_id']),
        ]

    def __str__(self):
        return f"Event {self.event_id} - {self.event_type} by {self.player_id}"


class ShotEvent(models.Model):
    """ShotEvent model for shot event details"""
    POINTS_CHOICES = [
        (0, '0 Points'),
        (2, '2 Points'),
        (3, '3 Points'),
    ]

    event_id = models.OneToOneField(Event, on_delete=models.CASCADE, primary_key=True, db_column='event_id')
    shot_result = models.CharField(max_length=20, null=True, blank=True)
    points = models.IntegerField(choices=POINTS_CHOICES, validators=[MinValueValidator(0), MaxValueValidator(3)])

    class Meta:
        db_table = 'app.shot_events'

    def __str__(self):
        return f"Shot Event {self.event_id} - {self.points} points"


class PassEvent(models.Model):
    """PassEvent model for pass event details"""
    event_id = models.OneToOneField(Event, on_delete=models.CASCADE, primary_key=True, db_column='event_id')
    target_player_id = models.ForeignKey(Player, on_delete=models.CASCADE, db_column='target_player_id', null=True, blank=True, related_name='received_passes')
    completed_pass = models.BooleanField(null=False)
    potential_assist = models.BooleanField(default=False)
    turnover = models.BooleanField(default=False)

    class Meta:
        db_table = 'app.pass_events'

    def __str__(self):
        return f"Pass Event {self.event_id} - {'Completed' if self.completed_pass else 'Failed'}"


class TurnoverEvent(models.Model):
    """TurnoverEvent model for turnover event details"""
    event_id = models.OneToOneField(Event, on_delete=models.CASCADE, primary_key=True, db_column='event_id')
    turnover_type = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'app.turnover_events'

    def __str__(self):
        return f"Turnover Event {self.event_id} - {self.turnover_type}"
