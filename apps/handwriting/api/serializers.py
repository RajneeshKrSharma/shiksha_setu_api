from rest_framework import serializers


class PageTextOut(serializers.Serializer):
    name = serializers.CharField()
    text = serializers.CharField(allow_blank=True)
