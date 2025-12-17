from rest_framework import serializers
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source='customer.name', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'product', 'rating',
                  'comment', 'customer_name', 'created_at']
        read_only_fields = ['customer']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['customer'] = user.customer
        return super().create(validated_data)
