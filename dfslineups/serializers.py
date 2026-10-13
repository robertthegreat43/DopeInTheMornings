
from rest_framework import serializers, viewsets
from dfslineups.models import Player, WeekPerformance, FullLineup, LosingLineup, WinningLineup


class WeekPerformanceSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source='player.name')

    class Meta:
        model = WeekPerformance
        fields = ('player_name', 'week', 'points')




class PlayerSerializer(serializers.ModelSerializer):
    WeekPerformances = WeekPerformanceSerializer(many=True, read_only=True)

    class Meta:
        model = Player
        fields = [
            'id',
            'name',
            'position',
            'team',
            'opponent',
            'salary',
            'projection',
            'ownership',
            'week',
            'game',
            'WeekPerformances',
        ]


class FullLineupSerializer(serializers.ModelSerializer):
    class Meta:
        model = FullLineup
        fields = "__all__"

class LosingLineupSerializer(serializers.ModelSerializer):
    class Meta:
        model = LosingLineup
        fields = ['id', 'lineup', 'reason', 'created_at']

class WinningLineupSerializer(serializers.ModelSerializer):
    class Meta:
        model = WinningLineup
        fields = ['id', 'lineup', 'score', 'created_at']

