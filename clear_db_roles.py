from django.db import connection
from accounts.models import User

def clear_roles():
    roles_to_clear = ['customer', 'worker', 'federation', 'society']
    try:
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF')
            print("Foreign keys disabled.")

            deleted_count = User.objects.filter(role__in=roles_to_clear).delete()[0]
            print(f"Deleted {deleted_count} users and related records from roles: {roles_to_clear}")

            cursor.execute('PRAGMA foreign_keys = ON')
            print("Foreign keys enabled.")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == '__main__':
    clear_roles()
