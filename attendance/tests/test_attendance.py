# attendance/tests/test_attendance.py
from django.test import TestCase
from django.urls import reverse
from datetime import date
from attendance.models import Attendance, AttendanceLog
from classes_app.models import ClassProgram
from students.models import Student
from teachers.models import Teacher

class AttendanceTests(TestCase):
    def setUp(self):
        # Try to fetch an existing teacher
        try:
            self.teacher = Teacher.objects.first()
        except Teacher.DoesNotExist:
            raise RuntimeError("No Teacher found in the database. Please create one before running tests.")

        self.user = self.teacher.user
        self.school = self.teacher.school

        # Grab an existing class program in that school
        self.class_program = ClassProgram.objects.filter(school=self.school).first()
        if not self.class_program:
            raise RuntimeError("No ClassProgram found for this teacher's school.")

        # Grab an existing student in that class
        self.student = Student.objects.filter(
            class_program=self.class_program, school=self.school
        ).first()
        if not self.student:
            raise RuntimeError("No Student found in that ClassProgram.")

        # Log in the teacher
        self.client.force_login(self.user)

    def test_edit_creates_attendance(self):
        url = reverse("attendance:edit")
        resp = self.client.post(url, {
            "student_id": self.student.id,
            "class_program_id": self.class_program.id,
            "date": date.today().isoformat(),
            "status": "PRESENT",
        })
        self.assertEqual(resp.status_code, 200)

        att = Attendance.objects.get(
            student=self.student,
            class_program=self.class_program,
            date=date.today()
        )
        self.assertEqual(att.status, "PRESENT")
        self.assertTrue(
            AttendanceLog.objects.filter(attendance=att, new_status="PRESENT").exists()
        )

    def test_edit_updates_attendance_and_logs_change(self):
        att, _ = Attendance.objects.get_or_create(
            student=self.student,
            class_program=self.class_program,
            date=date.today(),
            defaults={"status": "ABSENT", "marked_by": self.teacher}
        )

        url = reverse("attendance:edit")
        resp = self.client.post(url, {
            "student_id": self.student.id,
            "class_program_id": self.class_program.id,
            "date": date.today().isoformat(),
            "status": "PRESENT",
        })
        self.assertEqual(resp.status_code, 200)

        att.refresh_from_db()
        self.assertEqual(att.status, "PRESENT")
        log = AttendanceLog.objects.filter(attendance=att).latest("changed_at")
        self.assertEqual(log.new_status, "PRESENT")

    def test_bulk_present_marks_all(self):
        students = Student.objects.filter(class_program=self.class_program, school=self.school)
        url = reverse("attendance:bulk_present")
        resp = self.client.post(url, {
            "class_program_id": self.class_program.id,
            "date": date.today().isoformat(),
            "student_ids[]": [s.id for s in students],
        })
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(
            Attendance.objects.filter(
                class_program=self.class_program,
                date=date.today(),
                status="PRESENT"
            ).count(),
            students.count()
        )

    def test_roster_api_returns_students_with_status(self):
        Attendance.objects.get_or_create(
            student=self.student,
            class_program=self.class_program,
            date=date.today(),
            defaults={"status": "LATE", "marked_by": self.teacher}
        )

        url = reverse("attendance:roster_api")
        resp = self.client.get(url, {
            "class_program_id": self.class_program.id,
            "date": date.today().isoformat()
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(
            any(s["id"] == self.student.id and s["status"] == "LATE" for s in data)
        )
