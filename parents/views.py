from decimal import Decimal
from email.mime import message
import json
from datetime import date
from venv import logger
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import View

from .forms import CombinedParentProfileForm
from django.views.generic import TemplateView, DetailView, ListView, UpdateView, FormView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from core.mixins import RoleRequiredMixin, UserScopedMixin
from fees.models import Invoice, Payment
from django.db.models import Sum, Q, F, DecimalField, ExpressionWrapper
from .models import ParentProfile
from students.models import Student
from attendance.models import Attendance, AttendanceLog
from fees.models import Invoice
from django.db import transaction

from django.utils import timezone


# 1) Dashboard: list all your children

from django.utils import timezone
from django.views.generic import TemplateView
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from attendance.models import Attendance
from fees.models import Invoice
from .models import ParentProfile
from core.mixins import RoleRequiredMixin


class ParentDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "parents/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile: ParentProfile = self.request.user.parent_profile

        # Dates
        today = timezone.now().date()
        month_start = today.replace(day=1)

        # Children
        children = profile.children.select_related("class_program", "division")

        # Attendance (batch query for all children this month)
        attendance_qs = Attendance.objects.filter(
            student__in=children, date__gte=month_start
        ).select_related("student")

        # Group by student_id
        attendance_by_student = {}
        for att in attendance_qs:
            attendance_by_student.setdefault(att.student_id, []).append(att)

        # Invoices (batch query for all children)
        outstanding_expr = ExpressionWrapper(
            F("amount_due") - F("amount_paid"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
        invoices_qs = Invoice.objects.for_user(self.request.user).filter(
            student__in=children
        ).annotate( outstanding=F("amount_due") - F("amount_paid")
)

        invoices_by_student = {}
        for inv in invoices_qs:
            invoices_by_student.setdefault(inv.student_id, []).append(inv)

        # Enrich children data
        enriched = []
        for child in children:
            child_attendance = attendance_by_student.get(child.id, [])
            child_invoices = invoices_by_student.get(child.id, [])

            # Attendance today
            today_record = next((a for a in child_attendance if a.date == today), None)
            if today_record:
                if today_record.status == Attendance.Status.PRESENT:
                    attendance_today = "present"
                elif today_record.status == Attendance.Status.ABSENT:
                    attendance_today = "absent"
                else:
                    attendance_today = "partial"
            else:
                attendance_today = "pending"

            # Attendance % this month
            total_days = len(child_attendance)
            present_days = sum(1 for a in child_attendance if a.status == Attendance.Status.PRESENT)
            attendance_percent = int((present_days / total_days) * 100) if total_days else None

            # Finance summary
            unpaid_count = sum(1 for i in child_invoices if i.status == "UNPAID" or i.status == 'OPENING_BALANCE')
            partial_count = sum(1 for i in child_invoices if i.status == "PARTIAL")
            next_due = (
                min((i.due_date for i in child_invoices if i.status in ["UNPAID", "PARTIAL", 'OPENING_BALANCE']), default=None)
            )
            total_balance = sum(i.balance for i in child_invoices)

            enriched.append({
                "id": child.id,
                "full_name": child.full_name,
                "initial": child.full_name[:1].upper(),
                "class_program": getattr(child.class_program, "name", "—"),
                "division": getattr(child.division, "name", "—"),
                "attendance_today": attendance_today,
                "attendance_percent": attendance_percent,
                "unpaid_count": unpaid_count,
                "partial_count": partial_count,
                "next_due_date": next_due,
                "total_balance": total_balance,
            })

        ctx["children"] = enriched

        # ----- Attendance Summary (all children) -----
        total_records = len(attendance_qs)
        absences = sum(1 for a in attendance_qs if a.status == Attendance.Status.ABSENT)
        presents = sum(1 for a in attendance_qs if a.status == Attendance.Status.PRESENT)
        late_half = sum(
            1 for a in attendance_qs if a.status in [Attendance.Status.LATE, Attendance.Status.HALF_DAY]
        )
        attendance_rate = int((presents / total_records) * 100) if total_records else 0

        ctx.update({
            "absences_this_month": absences,
            "attendance_rate": attendance_rate,
            "presents_this_month": presents,
            "late_half_this_month": late_half,
        })

        # ----- Fees Summary (all children) -----
        unpaid_count = invoices_qs.filter(Q(status="UNPAID") | Q(status="OPENING_BALANCE")).count()
        partial_count = invoices_qs.filter(status="PARTIAL").count()
        total_outstanding = invoices_qs.aggregate(total=Sum("outstanding"))["total"] or 0
        next_due = invoices_qs.filter(status__in=["UNPAID", "PARTIAL", 'OPENING_BALANCE']).order_by("due_date").first()

        ctx.update({
            "unpaid_count": unpaid_count,
            "partial_count": partial_count,
            "total_outstanding": total_outstanding,
            "next_due_date": next_due.due_date if next_due else None,
            "upcoming_invoices": list(invoices_qs.filter(status__in=["UNPAID", "PARTIAL"]).order_by("due_date")[:3]),
        })
    
        return ctx

class ParentProfileView(LoginRequiredMixin, TemplateView):
    """
    Displays the parent's profile, linked children, and Telegram connection status.
    """
    template_name = "parents/profile.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Ensure the ParentProfile exists for the logged-in user
        parent_profile = get_object_or_404(ParentProfile, user=user)
        
        # --- TELEGRAM DEEP LINK SETUP ---
        # 1. Define the bot username (without the '@' symbol)
        bot_username = "dartsolutions_bot" 
        
        # 2. Define the unique start parameter (e.g., parent_123)
        start_param = f"parent_{parent_profile.id}"
        
        ctx.update({
            "user": user,
            "parent_profile": parent_profile,
            # Fetch all linked children (assuming a reverse relation named 'children')
            "children": parent_profile.children.all() if hasattr(parent_profile, "children") else [],
            
            # Pass Telegram parameters to the template for deep linking
            "bot_username": bot_username,
            "start_param": start_param,
        })
        
        return ctx
    
class EditParentProfileView(LoginRequiredMixin, FormView):
    """
    Handles updating both the core User model fields (name, email) 
    and the related ParentProfile model fields in a single form view.
    """
    template_name = "parents/edit_profile.html"
    form_class = CombinedParentProfileForm
    
    def get_form_kwargs(self):
        """Pass the current user instance to the form for validation."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    
    def get_context_data(self, **kwargs):
        """Adds the profile instance to the template context."""
        context = super().get_context_data(**kwargs)
        # Fetch and add the profile object
        context['parent_profile'] = get_object_or_404(ParentProfile, user=self.request.user)
        return context

    def get_initial(self):
        """Pre-populate the form with current user and profile data."""
        user = self.request.user
        # The key fix: getting the profile instance. get_object_or_404 expects the Model class as the first arg.
        profile = get_object_or_404(ParentProfile, user=user) 

        initial = super().get_initial()
        
        # Initial data from User model
        initial['first_name'] = user.first_name
        initial['last_name'] = user.last_name
        initial['email'] = user.email
        
        # Initial data from ParentProfile model
        initial['phone_number'] = profile.phone_number
        initial['telegram_username'] = profile.telegram_username
        
        # Pass the user's primary key for email clean method (as defined in forms.py)
        initial['user_pk'] = user.pk 
        
        return initial

    @transaction.atomic
    def form_valid(self, form):
        """Process the form data and save changes to both models."""
        user = self.request.user
        profile = get_object_or_404(ParentProfile, user=user)

        # 1. Update User Model
        user.first_name = form.cleaned_data.get('first_name')
        user.last_name = form.cleaned_data.get('last_name')
        user.email = form.cleaned_data.get('email')
        user.save()

        # 2. Update ParentProfile Model
        profile.phone_number = form.cleaned_data.get('phone_number')
        profile.telegram_username = form.cleaned_data.get('telegram_username')
        
        # Handle avatar upload 
        if form.cleaned_data.get('avatar'): # Check if a new file was uploaded
            profile.avatar = form.cleaned_data['avatar']
        elif form.cleaned_data.get('avatar_clear'): # Check if the user wants to clear the current avatar
            profile.avatar = None

        profile.save()
            
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("parents:profile")
    
class ChildDetailView(RoleRequiredMixin, DetailView):
    model = Student
    template_name = "parents/child_detail.html"
    context_object_name = "child"

    def get_queryset(self):
        # Limit to children of this parent
        profile = self.request.user.parent_profile
        return profile.children.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        child = self.object

        # Attendance history (last 30 days)
        ctx["attendance_records"] = Attendance.objects.filter(
            student=child
        ).order_by("-date")[:30]

        # Invoices
        invoices = Invoice.objects.for_user(self.request.user).filter(student=child)
        ctx["invoices"] = invoices.order_by("-due_date")[:10]

        # Outstanding balance
        outstanding_expr = ExpressionWrapper(
            F("amount_due") - F("amount_paid"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
        ctx["total_balance"] = invoices.aggregate(total=Sum(outstanding_expr))["total"] or 0

        return ctx
# 3) Attendance history for one child
class ChildAttendanceListView(RoleRequiredMixin, UserScopedMixin, ListView):
    model = AttendanceLog
    template_name = "parents/attendance_list.html"
    context_object_name = "attendance_records"
    paginate_by = 20

    def get_queryset(self):
        child = get_object_or_404(
          self.request.user.parent_profile.children, pk=self.kwargs["pk"]
        )
        return AttendanceLog.objects.filter(student=child).order_by("-date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["child"] = get_object_or_404(
            self.request.user.parent_profile.children, pk=self.kwargs["pk"]
        )
        return ctx



class KidsView(RoleRequiredMixin, TemplateView):
    template_name = "parents/kids.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.request.user.parent_profile
        children = profile.children.select_related("class_program", "division")

        today = timezone.now().date()
        month_start = today.replace(day=1)

        enriched = []
        for child in children:
            # Attendance today
            record = Attendance.objects.filter(student=child, date=today).first()
            if record:
                if record.status == Attendance.Status.PRESENT:
                    attendance_today = "present"
                elif record.status == Attendance.Status.ABSENT:
                    attendance_today = "absent"
                else:
                    attendance_today = "partial"
            else:
                attendance_today = "pending"

            # Attendance % this month
            total = Attendance.objects.filter(student=child, date__gte=month_start).count()
            present = Attendance.objects.filter(
                student=child, date__gte=month_start, status=Attendance.Status.PRESENT
            ).count()
            attendance_percent = int((present / total) * 100) if total else None

            # Finance summary
            invoices = Invoice.objects.for_user(self.request.user).filter(student=child)
            unpaid_count = invoices.filter(status="UNPAID").count()
            partial_count = invoices.filter(status="PARTIAL").count()
            next_due = invoices.filter(status__in=["UNPAID","PARTIAL"]).order_by("due_date").first()
            total_balance = invoices.aggregate(
                total=Sum(F("amount_due") - F("amount_paid"))
            )["total"] or 0

            enriched.append({
                "id": child.id,
                "full_name": child.full_name,
                "initial": child.full_name[:1].upper(),
                "class_program": getattr(child.class_program, "name", "—"),
                "division": getattr(child.division, "name", "—"),
                "attendance_today": attendance_today,
                "attendance_percent": attendance_percent,
                "unpaid_count": unpaid_count,
                "partial_count": partial_count,
                "next_due_date": next_due.due_date if next_due else None,
                "total_balance": total_balance,
            })

        ctx["children"] = enriched
        return ctx


class FeesView(RoleRequiredMixin, TemplateView):
    template_name = "parents/fees.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.request.user.parent_profile
        children = list(profile.children.select_related("class_program", "division"))

        # All invoices for this parent (for all children)
        invoices = list(
            Invoice.objects.for_user(self.request.user)
            .filter(student__in=children)
            .select_related("student", "fee")
            .order_by("-due_date")
        )
        payments = (
    Payment.objects
    .filter(invoice__in=invoices)
    .select_related('invoice') # Optional, good
    .order_by('-paid_on') 
)
        # Group invoices and compute per-child summary
        children_data = []
        invoices_by_child = {}
        for inv in invoices:
            invoices_by_child.setdefault(inv.student_id, []).append(inv)

        for child in children:
            child_invoices = invoices_by_child.get(child.id, [])
            unpaid = [inv for inv in child_invoices if inv.status in ["UNPAID", "OPENING_BALANCE"]]
            partial = [inv for inv in child_invoices if inv.status == "PARTIAL"]
            total_balance = sum(
                getattr(inv, "balance", getattr(inv, "amount_due", 0) - getattr(inv, "amount_paid", 0))
                for inv in child_invoices
            ) if child_invoices else 0
            next_due = None
            next_candidates = sorted(unpaid + partial, key=lambda x: x.due_date) if (unpaid or partial) else []
            if next_candidates:
                next_due = next_candidates[0].due_date
                
            

            children_data.append({
                "child": child,
                "unpaid_count": len(unpaid),
                "partial_count": len(partial),
                "total_balance": total_balance,
                "next_due_date": next_due,
                "invoices_count": len(child_invoices),
            })

        # Global totals
        if invoices:
            total_balance = sum(
                getattr(inv, "balance", getattr(inv, "amount_due", 0) - getattr(inv, "amount_paid", 0))
                for inv in invoices
            )

            total_unpaid = sum(
                getattr(inv, "amount_due", 0) - getattr(inv, "amount_paid", 0)
                for inv in invoices
                if getattr(inv, "status", "").upper() != "PAID"
            )

            total_paid = sum(
                getattr(inv, "amount_paid", 0)
                for inv in invoices
                if getattr(inv, "status", "").upper() == "PAID"
            )
        else:
            total_balance = total_unpaid = total_paid = 0

        ctx["children_data"] = children_data
        ctx["total_balance"] = total_balance
        ctx["total_paid"] = total_paid
        ctx["total_unpaid"] = total_unpaid
        ctx["invoice_count"] = len(invoices)
        ctx["payments"] = payments

        
        return ctx

class ParentReportsView(RoleRequiredMixin, TemplateView):
    template_name = "parents/reports.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile: ParentProfile = self.request.user.parent_profile
        children = list(profile.children.select_related("class_program", "division"))

        # Get current month start
        today = timezone.now().date()
        month_start = today.replace(day=1)

        # Pre-fetch all attendance for current month
        attendance_qs = Attendance.objects.filter(
            student__in=children, date__gte=month_start
        )
        attendance_by_student = {}
        for att in attendance_qs:
            attendance_by_student.setdefault(att.student_id, []).append(att)

        # Pre-fetch invoices for all children
        invoices_qs = Invoice.objects.for_user(self.request.user).filter(student__in=children)
        invoices_by_student = {}
        for inv in invoices_qs:
            invoices_by_student.setdefault(inv.student_id, []).append(inv)

        children_data = []
        for child in children:
            # Attendance
            records = attendance_by_student.get(child.id, [])
            total_days = len(records)
            present_days = sum(1 for a in records if a.status == Attendance.Status.PRESENT)
            attendance_percent = round((present_days / total_days) * 100) if total_days else None
            

            # Today's attendance
            today_record = next((a for a in records if a.date == today), None)
            if today_record:
                attendance_today = today_record.status.lower()
            else:
                attendance_today = "pending"

            # Invoices
            child_invoices = invoices_by_student.get(child.id, [])
            unpaid_count = sum(1 for i in child_invoices if i.status in ["UNPAID", "OPENING_BALANCE"])
            partial_count = sum(1 for i in child_invoices if i.status == "PARTIAL")
            next_due = min((i.due_date for i in child_invoices if i.status in ["UNPAID", "PARTIAL", "OPENING_BALANCE"]), default=None)
            total_balance = sum(getattr(i, "balance", getattr(i, "amount_due", 0) - getattr(i, "amount_paid", 0)) for i in child_invoices)

            children_data.append({
                "child": child,
                "attendance_percent": attendance_percent,
                "attendance_today": attendance_today,
                "unpaid_count": unpaid_count,
                "partial_count": partial_count,
                "total_balance": total_balance,
                "next_due_date": next_due,
            })

        ctx["children_data"] = children_data
        

        # Summary cards
        ctx["total_children"] = len(children)
        ctx["total_unpaid"] = sum(c["unpaid_count"] for c in children_data)
        ctx["total_partial"] = sum(c["partial_count"] for c in children_data)
        ctx["total_outstanding"] = sum(c["total_balance"] for c in children_data)
        ctx["next_due_date"] = min([c["next_due_date"] for c in children_data if c["next_due_date"]], default=None)

        # Overall attendance rate
        attendance_values = [c["attendance_percent"] for c in children_data if c["attendance_percent"] is not None]
        ctx["attendance_rate"] = round(sum(attendance_values) / len(attendance_values)) if attendance_values else None

        # Chart data
        ctx["attendance_labels"] = [c["child"].full_name for c in children_data]
        ctx["attendance_values"] = [c["attendance_percent"] or 0 for c in children_data]
        ctx["payment_labels"] = ["Paid", "Partial", "Unpaid"]
        ctx["payment_values"] = [
            sum(i.total_balance for i in children_data if i["total_balance"] and i["total_balance"] == 0),
            ctx["total_partial"],
            ctx["total_unpaid"]
        ]

        return ctx

class ChildFeesDetailView(RoleRequiredMixin, TemplateView):
    """
    Detail page for a single child showing grouped invoices and
    the same simplified structure as the child detail page.
    """
    template_name = "parents/child_fees_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.request.user.parent_profile
        child_pk = self.kwargs.get("pk")
        # ensure parent only accesses their own child
        child = get_object_or_404(profile.children, pk=child_pk)
        ctx["child"] = child

        # invoices for this child
        invoices = (
            Invoice.objects.for_user(self.request.user)
            .filter(student=child, status__in = ["OPENING_BALANCE", "UNPAID"])
            .select_related("fee")
            .order_by("-due_date")
        )
        ctx["invoices"] = invoices

        # summary for this child
        unpaid = invoices.filter(status__in=["UNPAID", "OPENING_BALANCE"]).count()
        partial = invoices.filter(status="PARTIAL").count()
        paid = invoices.filter(status="PAID").count()
        expr = ExpressionWrapper(F("amount_due") - F("amount_paid"), output_field=DecimalField(max_digits=12, decimal_places=2))
        total_balance = invoices.aggregate(total=Sum(expr))["total"] or 0
        next_due_qs = invoices.filter(status__in=["UNPAID", "PARTIAL", "OPENING_BALANCE"]).order_by("due_date")
        next_due = next_due_qs.first().due_date if next_due_qs.exists() else None
        

        ctx["summary"] = {
            "unpaid_count": unpaid,
            "partial_count": partial,
            "paid_count": paid,
            "total_balance": total_balance,
            "next_due_date": next_due,
        }

        child_invoices = Invoice.objects.filter(student=child)
        
        # 2. Filter Payments associated with those invoices, order by most recent
        payments = (
            Payment.objects
            .filter(invoice__in=child_invoices)
            .select_related('invoice') # Optional, but good practice
            .order_by('-paid_on') 
        )
        
        ctx["payments"] = payments
        return ctx

# payments/views.py
import json
from decimal import Decimal
from django.db import transaction
from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from django.utils import timezone

class ProcessPaymentView(View):
    """
    Accepts payment submissions:
    - JSON body (application/json) for mobile money/online flows (parent provides external id)
    - multipart/form-data for bank transfer (allows receipt_file)
    """
    def post(self, request, pk):
        try:
            # ensure parent owns the child
            profile = request.user.parent_profile
            child = get_object_or_404(profile.children, pk=pk)

            # Parse input
            if request.content_type.startswith('multipart/'):
                data = request.POST
                files = request.FILES
            else:
                data = json.loads(request.body.decode('utf-8') or "{}")
                files = None

            invoice_ids = data.get('invoice_ids') or data.get('invoice_ids[]')
            # invoice_ids might be comma separated string
            if isinstance(invoice_ids, str):
                invoice_ids = [x.strip() for x in invoice_ids.split(',') if x.strip()]
            try:
                invoice_ids = list(map(int, invoice_ids))
            except Exception:
                return JsonResponse({"message": "Invalid invoice IDs."}, status=400)

            method = data.get('method')
            amount = Decimal(str(data.get('amount', '0') or '0'))
            provider = data.get('mobile_provider') or data.get('provider')
            external_tx = data.get('reference') or data.get('external_transaction_id') or data.get('external_transaction')
            receipt_type = data.get('receipt_type', 'single')

            if not invoice_ids or not method or amount <= 0:
                return JsonResponse({"message": "Missing required payment data."}, status=400)

            # lock invoices
            invoices_qs = Invoice.objects.select_for_update().filter(id__in=invoice_ids, student=child).select_related('school')
            if invoices_qs.count() != len(invoice_ids):
                return JsonResponse({"message": "Invalid invoice selection."}, status=400)

            is_bank = method == 'Bank Transfer'
            is_mobile_money = method == 'Mobile Money'
            is_cash = method.lower() == 'cash' or method == 'cash (office)'
            is_online = method == 'Online'

            if (is_mobile_money or is_online) and not external_tx:
                 return JsonResponse({"message": f"{method} payment requires a Reference / Transaction ID."}, status=400)

            # total outstanding (amounts outstanding per invoice)
            total_due = sum([ (inv.amount_due - (inv.amount_paid or Decimal('0'))) for inv in invoices_qs ])
            # require exact payment (no partials)
            if amount != total_due:
                return JsonResponse({"message": "Amount must equal total outstanding for selected invoices."}, status=400)

            created = []
            with transaction.atomic():
                for inv in invoices_qs:
                    outstanding = (inv.amount_due - (inv.amount_paid or Decimal('0')))
                    if outstanding <= 0:
                        continue

                    # decide status
                    if is_bank:
                        pay_status = Payment.STATUS_UNCONFIRMED
                    elif is_mobile_money:
                        # if external_tx provided, we create PENDING and rely on webhook
                        pay_status = Payment.STATUS_PENDING
                    elif is_cash:
                        pay_status = Payment.STATUS_CONFIRMED
                    else:
                        # Online (card) or others: start PENDING and verify via gateway/webhook
                        pay_status = Payment.STATUS_PENDING

                    p = Payment.objects.create(
                        school=inv.school,
                        invoice=inv,
                        amount=outstanding,
                        paid_on=timezone.now(),
                        method=method,
                        provider=(provider if provider else None),
                        external_transaction_id=(external_tx if external_tx else None),
                        receipt_file=(files.get('receipt_file') if files and files.get('receipt_file') else None),
                        status=pay_status,
                        paid_by=(request.user if request.user.is_authenticated else None),
                        received_by=(request.user if request.user.is_authenticated else None),
                        receipt_type=receipt_type,
                        reference=(external_tx if external_tx else None),
                    )

                    # Only update invoice if payment is CONFIRMED (e.g. Cash)
                    if p.status == Payment.STATUS_CONFIRMED:
                        inv.amount_paid = (inv.amount_paid or Decimal('0')) + p.amount
                        inv.status = 'PAID' if inv.amount_paid >= inv.amount_due else 'PARTIAL'
                        inv.save(update_fields=['amount_paid','status'])
                    else:
                        # For PENDING/UNCONFIRMED, we leave invoice unchanged but we may want to flag it
                        # Optionally add a flag/invoice.note for "pending payment"
                        pass

                    created.append(p)

            resp = {
                "message": "Payment recorded",
                "payments": [{"id": p.id, "status": p.status, "reference": p.external_transaction_id or str(p.id)} for p in created],
                "total": str(amount)
            }
            if any(p.status == Payment.STATUS_UNCONFIRMED for p in created):
                resp['note'] = "Bank transfer uploaded — awaiting confirmation by school staff."
            if any(p.status == Payment.STATUS_PENDING for p in created):
                resp['note'] = resp.get('note','') + " Payment pending provider confirmation."

            return JsonResponse(resp, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON payload."}, status=400)
        except Exception as e:
            return JsonResponse({"message": f"Server error: {str(e)}"}, status=500)

# payments/views.py
import uuid
from django.views import View
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseBadRequest

class ProviderRedirectView(View):
    """
    Creates a server-side PENDING Payment placeholder (one per invoice), generates a merchant_order_id,
    and redirects to the provider checkout URL (TeleBirr / M-Pesa).
    """
    def get(self, request):
        provider = request.GET.get('provider')
        amount = request.GET.get('amount')
        invoice_ids = request.GET.get('invoice_ids')  # comma-separated
        return_url = request.GET.get('return_url')  # where provider will redirect user after payment

        if not provider or not amount or not invoice_ids:
            return HttpResponseBadRequest("Missing params")

        try:
            invoice_ids_list = [int(x.strip()) for x in invoice_ids.split(',') if x.strip()]
        except ValueError:
            return HttpResponseBadRequest("Invalid invoice ids")

        # Optionally validate parent owns these invoices here (requires child pk or session)
        # Create a merchant_order_id to track this transaction
        merchant_order = str(uuid.uuid4())

        # create Payment placeholders (status=PENDING) for each invoice (or one aggregated record)
        invoices = Invoice.objects.filter(id__in=invoice_ids_list).select_related('school')
        with transaction.atomic():
            for inv in invoices:
                Payment.objects.create(
                    school=inv.school,
                    invoice=inv,
                    amount=(inv.amount_due - (inv.amount_paid or 0)),
                    paid_on=timezone.now(),
                    method='Mobile Money',
                    provider=provider,
                    external_transaction_id=merchant_order,  # temp correlation
                    status=Payment.STATUS_PENDING,
                    paid_by=(request.user if request.user.is_authenticated else None),
                    received_by=None,
                )

        # Build provider url (replace with real API and signed payload)
        callback_url = request.build_absolute_uri(reverse('payments:provider_callback'))  # webhook endpoint
        # Example: provider_base + params (IN REAL LIFE: you sign payload server-side and POST)
        provider_checkout = f"https://pay.example.com/checkout?provider={provider}&amount={amount}&merchant_order={merchant_order}&callback={callback_url}&return_url={return_url}"
        return redirect(provider_checkout)




#Running the bot automatically

from django.http import JsonResponse, HttpResponse
import json
import threading
import logging # <-- CRITICAL: Must import or define logger here
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from bot.main import process_update_sync # Import the function

logger = logging.getLogger(__name__)  # <-- CRITICAL: Define logger here

@csrf_exempt
def telegram_webhook(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            process_update_sync(data)
            return JsonResponse({"ok": True})
        except Exception as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=500)
    # GET or other methods
    return JsonResponse({"error": "Method not allowed"}, status=405)

from django.http import JsonResponse
from django.views import View
from fees.models import Invoice
from parents.models import ParentProfile

class ParentFeeSummaryView(View):
    def get(self, request, parent_id):
        # Filter invoices of all children belonging to this parent
        print('parent fees summary is called and we find the parent_id', parent_id)
        invoices = (
            Invoice.objects
            .filter(
                student__parents__id=parent_id,
                status__in=["UNPAID", "PARTIAL", "OPENING_BALANCE"]
            )
            .select_related("student")
            .order_by("due_date")
        )

        grouped = {}

        for inv in invoices:
            student_name = inv.student.full_name
            if student_name not in grouped:
                grouped[student_name] = {
                    "student_id": inv.student.id,
                    "student_name": student_name,
                    "count": 0,
                    "total": 0,
                    "nearest_due": None,
                }

            grouped[student_name]["count"] += 1

            # Compute outstanding balance
            balance = getattr(
                inv,
                "balance",
                getattr(inv, "amount_due", 0) - getattr(inv, "amount_paid", 0)
            )
            grouped[student_name]["total"] += balance

            due = inv.due_date
            if not grouped[student_name]["nearest_due"] or (due and due < grouped[student_name]["nearest_due"]):
                grouped[student_name]["nearest_due"] = due

        return JsonResponse(list(grouped.values()), safe=False)

class StudentFeeSummaryView(View):
    """
    New view required for the Telegram bot's "Back" button.
    It summarizes unpaid fees for a SINGLE student ID.
    Returns a single student summary dictionary.
    """
    def get(self, request, student_id):
        # 1. Filter invoices only for the specific student ID
        invoices = (
            Invoice.objects
            .filter(
                student__id=student_id, # Filter directly by student ID
                status__in=["UNPAID", "PARTIAL", "OPENING_BALANCE"]
            )
            .select_related("student")
            .order_by("due_date")
        )

        # If no unpaid invoices exist, return an empty JSON object
        if not invoices.exists():
            return JsonResponse({}, safe=False)

        # 2. Initialize and process summary for the single student
        inv_student = invoices.first().student
        student_summary = {
            "student_id": inv_student.id,
            "student_name": inv_student.full_name,
            "count": 0,
            "total": Decimal(0),
            "nearest_due": None,
        }

        for inv in invoices:
            student_summary["count"] += 1

            # Compute outstanding balance (using the existing logic)
            balance = getattr(
                inv,
                "balance",
                getattr(inv, "amount_due", 0) - getattr(inv, "amount_paid", 0)
            )
            student_summary["total"] += Decimal(balance)

            due = inv.due_date
            # Find the nearest due date
            if not student_summary["nearest_due"] or (due and due < student_summary["nearest_due"]):
                student_summary["nearest_due"] = due

        # 3. Final serialization for JSON response
        response_data = {
            "student_id": student_summary["student_id"],
            "student_name": student_summary["student_name"],
            "count": student_summary["count"],
            "total": f"{student_summary['total']:.2f}",
            "nearest_due": student_summary["nearest_due"].isoformat() if student_summary["nearest_due"] else None,
        }
        
        # Return the single dictionary object as expected by the Telegram bot's "Back" handler
        return JsonResponse(response_data, safe=False)
    
class StudentUnpaidInvoicesView(View):
    """
    Returns unpaid/partial invoices for a specific student as JSON,
    so the bot can fetch them.
    """
    def get(self, request, student_id):
        # 1. Make sure student exists
        student = get_object_or_404(Student, id=student_id)

        # 2. Get unpaid or partial invoices for this student
        invoices = Invoice.objects.filter(
            student=student,
            status__in=["UNPAID", "PARTIAL", "OPENING_BALANCE"]
        ).select_related("student", "fee").order_by("due_date")

        data = []
        for inv in invoices:
            data.append({
                "invoice_id": inv.id,
                "invoice_name": inv.fee.name,
                "student_id": inv.student.id,
                "student_name": inv.student.full_name,
                "description": getattr(inv, "description", inv.fee.name if inv.fee else "N/A"),
                "amount_due": float(getattr(inv, "amount_due", 0)),
                "amount_paid": float(getattr(inv, "amount_paid", 0)),
                "balance": float(getattr(inv, "balance", getattr(inv, "amount_due", 0) - getattr(inv, "amount_paid", 0))),
                "due_date": inv.due_date.strftime("%Y-%m-%d") if inv.due_date else None,
                "status": inv.status,
            })

        return JsonResponse(data, safe=False)