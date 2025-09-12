from accounts.models import User
from students.models import Student
from classes_app.models import Division
from fees.models import FeeStructure
from datetime import date
import random

# SETTINGS
STUDENTS_PER_DIVISION = 300

# Realistic Ethiopian names
male_first_names = [
    "Abel", "Dawit", "Yohannes", "Tesfaye", "Bekele", "Solomon",
    "Kebede", "Mesfin", "Haile", "Tewodros", "Meles", "Asnake"
]
female_first_names = [
    "Marta", "Genet", "Almaz", "Hirut", "Selam", "Aster",
    "Sara", "Tsion", "Hanna", "Rahel", "Meaza", "Fikir"
]
last_names = [
    "Abebe", "Tadesse", "Gebremedhin", "Kebede", "Worku",
    "Tesfaye", "Demissie", "Bekele", "Negash", "Ayele"
]

def random_name():
    """Generate a realistic Ethiopian full name."""
    if random.choice([True, False]):
        first = random.choice(male_first_names)
    else:
        first = random.choice(female_first_names)
    return f"{first} {random.choice(last_names)}"

def random_billing_month():
    """Pick a random billing month between Jan and Aug 2025."""
    month = random.randint(1, 8)
    return date(2025, month, 1)

# Get school from ProfMelat
user = User.objects.get(username="ProfMelat")
school = user.school
print(f"🎯 Creating students for school: {school.name}")

# Get divisions
divisions = Division.objects.filter(school=school)
if not divisions.exists():
    raise ValueError("⚠️ No divisions found for this school. Please create some first!")

# Get fee structures
fee_structures = list(FeeStructure.objects.filter(school=school))
if not fee_structures:
    raise ValueError("⚠️ No fee structures found for this school. Please create some first!")

all_students = []

for division in divisions:
    print(f"📚 Adding {STUDENTS_PER_DIVISION} students to {division.name}...")
    if division.name == 'KINGERGARTEN':
        STUDENTS_PER_DIVISION = 330
    elif division.name =='PRIMARY_1_4':
        STUDENTS_PER_DIVISION = 498
    elif division.name == 'PRIMARY_5_8':
        STUDENTS_PER_DIVISION = '532'
    for _ in range(STUDENTS_PER_DIVISION):
        student = Student.objects.create(
            full_name=random_name(),
            division=division,
            starting_billing_month=random_billing_month(),
            opening_balance=random.choice([0, 500, 1000, 1500, 2500, 5000]),
            next_payment_date=None,
            school=school
        )
        # Assign 1-2 random fees
        student.fee_structures.set(random.sample(
            fee_structures,
            k=min(len(fee_structures), random.randint(1, 2))
        ))
        all_students.append(student)

print(f"✅ Created {len(all_students)} students in total.\n")

# Show a summary of first few students
print("🔍 Sample of created students:")
for s in all_students[:20]:
    print(f"{s.full_name} | Division: {s.division.name} | Start: {s.starting_billing_month} | OB: {s.opening_balance} | Fees: {[f.name for f in s.fee_structures.all()]}")
