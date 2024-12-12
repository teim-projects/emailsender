from django.db import models

# Create your models here.


from django.db import models

class UploadedTable(models.Model):
    table_name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.table_name
