from django.db import models


class Transaction(models.Model):
    transaction_id = models.CharField(max_length=50, unique=True)

    customer_id = models.CharField(max_length=50)
    customer_type = models.CharField(max_length=20)
    account_age_days = models.IntegerField()

    transaction_amount = models.FloatField()
    merchant_category = models.CharField(max_length=100)

    payment_status = models.CharField(max_length=20)

    fraud_label = models.BooleanField()
    fraud_score = models.FloatField(default=0.0)

    def __str__(self):
        return self.transaction_id

