from rest_framework import serializers
from .models import Review, Question


class QuestionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source='customer.name', read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'product', 'customer_name',
                  'question', 'answer', 'created_at']
        read_only_fields = ['customer']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['customer'] = request.user.customer
        return super().create(validated_data)

class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source='customer.name', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'product', 'rating',
                  'comment', 'customer_name', 'created_at']
        read_only_fields = ['customer']

    def validate(self, data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            customer = request.user.customer
            product = data.get('product')
            if Review.objects.filter(product=product, customer=customer).exists():
                raise serializers.ValidationError("You have already reviewed this product.")
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['customer'] = user.customer
        return super().create(validated_data)
