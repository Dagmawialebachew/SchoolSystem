from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
from django.views.generic import ListView, DetailView, TemplateView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from io import BytesIO
from django.db.models import Sum, Count, Q, Max
from reportlab.pdfgen import canvas
from .models import Invoice, Payment, FeeStructure, Student, PaymentReversal
from core.mixins import RoleRequiredMixin  # Adjust this if needed
from django.db.models import F, Sum
from .forms import InvoiceForm, FeeForm
from django.contrib import messages
from django.views import View
from datetime import date
from .forms import PaymentForm, PaymentReversalForm  
from .utilis import export_student_invoices_to_excel, export_student_invoices_to_pdf, generate_invoices_for_school
from decimal import Decimal
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Prefetch
from django.utils.timezone import now
from django.core.paginator import Paginator
from .utilis import export_invoices_to_excel, export_multiple_payment_receipts_pdf, export_separate_payment_receipts_zip
from datetime import datetime, timedelta
from django.core import signing
from django.db import transaction
from .utilis import make_receipt_token, generate_payments_pdf, generate_payments_excel
# ---------------- Dashboard ----------------
class FeesDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "fees/fee_dashboard.html"
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN", "ACCOUNTANT"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school = self.request.user.school

        total_revenue = (
            Payment.objects.filter(school=school).aggregate(total=Sum("amount"))["total"] or 0
        )
        pending_invoices = Invoice.objects.filter(school=school, status="PENDING").count()
        paid_invoices = Invoice.objects.filter(school=school, status="PAID").count()
        outstanding_balance = (
            Invoice.objects.filter(school=school)
            .annotate(balance=F("amount_due") - F("amount_paid"))
            .aggregate(total=Sum("balance"))["total"] or 0
        )
        context.update({
            "total_revenue": total_revenue,
            "pending_invoices": pending_invoices,
            "paid_invoices": paid_invoices,
            "outstanding_balance": outstanding_balance,
            "title": "Fees Dashboard",
            "subtitle": "Track invoices, revenue, and payments in real-time.",
            "add_url": reverse_lazy("fees:add_fee"),
            "add_button_text": "+ Add Fee",
            "active_tab": "dashboard",
        })
        return context


# ---------------- Fee Setup CRUD ----------------
class FeeListView(ListView):
    model = FeeStructure
    template_name = "fees/fee_list.html"
    context_object_name = "object_list"
    paginate_by = 10  # Show 10 per page

    def get_queryset(self):
        school = self.request.user.school  # 🔥 Limit to logged-in user's school
        queryset = FeeStructure.objects.filter(school=school).order_by("-created_at")
        search_query = self.request.GET.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context.update( {
            "title": "Fee Setup",
            "subtitle" : "Manage all fee structures for your school.",
            "add_url" : reverse_lazy("fees:add_fee"),
            "add_button_text" : "+ Add Fee",
            "active_tab" : "fees"
            
        })
        return context

class FeeCreateView(RoleRequiredMixin, CreateView):
    model = FeeStructure
    form_class = FeeForm
    template_name = "fees/fee_form.html"
    success_url = reverse_lazy("fees:fees_list")
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN", "ACCOUNTANT"]

    def form_valid(self, form):
        form.instance.school = self.request.user.school
        return super().form_valid(form)
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "title": "Create Fees",
            "subtitle": "Create a fee structure for students",
            "active_tab": "fees",
        })
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class FeeUpdateView(RoleRequiredMixin, UpdateView):
    model = FeeStructure
    template_name = "fees/fee_form.html"
    fields = ["name", "amount", "description"]
    success_url = reverse_lazy("fees:fees_list")
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN", "ACCOUNTANT"]

    def get_queryset(self):
        return FeeStructure.objects.filter(school=self.request.user.school)


class FeeDeleteView(RoleRequiredMixin, DeleteView):
    model = FeeStructure
    template_name = "fees/fee_confirm_delete.html"
    success_url = reverse_lazy("fees:fees_list")
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN", "ACCOUNTANT"]

    def get_queryset(self):
        return FeeStructure.objects.filter(school=self.request.user.school)


# ---------------- Invoice Views ----------------
class InvoiceListView(RoleRequiredMixin, ListView):
    model = Student
    template_name = "fees/invoice_list.html"
    context_object_name = "students"
    allowed_roles = ["ADMIN", "PARENT", "SCHOOL_ADMIN"]
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user

        queryset = Student.objects.filter(school=user.school).annotate(
            total_paid=Sum("invoices__amount_paid", filter=Q(invoices__school=user.school)),
            total_unpaid=Sum(
                "invoices__amount_due",
                filter=Q(invoices__school=user.school, invoices__status__in=["UNPAID", "OPENING_BALANCE"]),
            ),
            invoices_count=Count("invoices", filter=Q(invoices__school=user.school)),
        )
        

        # Parent filter
        if user.role == "PARENT":
            queryset = queryset.filter(parent=user)

        # Search
        search_query = self.request.GET.get("search", "").strip()
        selected_status = self.request.GET.get('status', '').strip()
        if search_query:
            queryset = queryset.filter(full_name__icontains=search_query)
        if selected_status:
            queryset = queryset.filter(invoices__status=selected_status)


        return queryset.order_by('-payment_status', '-total_unpaid')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "search_query": self.request.GET.get("search", ""),
            "status_choices": Invoice.STATUS_CHOICES,  # Assuming a Django Choices enum
            "selected_status": self.request.GET.get("status", ""),
            "title": "Invoices",
            "subtitle": "View and manage all student invoices",
            "add_url": reverse_lazy("fees:create_invoice"),
            "add_button_text": "+ Add Invoice",
            "active_tab": "invoices",
            "generate_url": True
        })
        return context
    
RECEIPT_TOKEN_MAX_AGE = 600 

class InvoiceDetailView(RoleRequiredMixin, DetailView):
    model = Student  # No change here, as we are still working with Student model
    template_name = "fees/invoice_detail.html"
    context_object_name = "student"
    allowed_roles = ["ADMIN", "PARENT", "SCHOOL_ADMIN"]

    def get_queryset(self):
        user = self.request.user
        qs = Student.objects.filter(school=user.school).prefetch_related(
            Prefetch('invoices', queryset=Invoice.objects.prefetch_related('payments'))
        )
        return qs.filter(parent=user) if user.role == "PARENT" else qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.get_object()
        
        # Get unpaid invoices for the student
        unpaid_invoices = student.invoices.filter(
            status__in=['UNPAID', 'OPENING_BALANCE'],
            school=self.request.user.school
        ).order_by('due_date')

        # If there are no unpaid invoices, show a message but still show payment history
        if not unpaid_invoices:
            context["no_unpaid_invoices_message"] = "No unpaid invoices for this student. Below is the payment history."

        # Get payment history related to unpaid invoices
        payment_history = Payment.objects.filter(invoice__student = student)

        # Update context with all the necessary details
        context.update({
            "payment_history": payment_history,
            "unpaid_invoices": unpaid_invoices,
            "has_unpaid": unpaid_invoices.exists(),
            "form": kwargs.get("form", PaymentForm()),
            "payment_methods": ["Cash", "Bank Transfer", "Mobile Money"],
            "title": f"{student.full_name} Invoices",
            "subtitle": "Invoice overview and payment history",
            "add_url": reverse_lazy("fees:invoices_list"),
            "add_button_text": "Back to invoices",
            "active_tab": "invoices",
            "payment_detail_url": reverse_lazy("fees:payment_detail", kwargs={"pk": student.pk}),
            'export': True

        })
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        student = self.get_object()
        form = PaymentForm(request.POST)

        if not form.is_valid():
            return self.get(request, *args, **kwargs)

        receipt_type = form.cleaned_data.get("receipt_type")
        invoice_ids_raw = request.POST.get('invoice_ids', '')
        selected_invoice_ids = [int(pk) for pk in invoice_ids_raw.split(',') if pk]

        if not selected_invoice_ids:
            messages.error(request, "Please select at least one invoice.")
            return self.get(request, *args, **kwargs)

        invoices_qs = student.invoices.filter(
            id__in=selected_invoice_ids,
            status__in=['UNPAID', 'OPENING_BALANCE'],
            school=request.user.school
        ).order_by('due_date')

        if not invoices_qs.exists():
            messages.error(request, "No eligible invoices selected.")
            return self.get(request, *args, **kwargs)

        total_amount = Decimal(form.cleaned_data['payment_amount'])
        if total_amount <= 0:
            messages.error(request, "Payment amount must be greater than zero.")
            return self.get(request, *args, **kwargs)

        # Calculate total due across the chosen invoices
        total_due = sum((inv.amount_due - inv.amount_paid) for inv in invoices_qs)
        if total_amount > total_due:
            messages.error(request, "The payment amount exceeds the total due for selected invoices.")
            return self.get(request, *args, **kwargs)

        allocations = []  # list of (invoice, paid_now)
        payments = []

        with transaction.atomic():
            # Lock invoices to avoid race conditions during concurrent pays
            invoices = (student.invoices
                        .select_for_update()
                        .filter(id__in=selected_invoice_ids,
                                status__in=['UNPAID', 'OPENING_BALANCE'],
                                school=request.user.school)
                        .order_by('due_date'))

            remaining = total_amount

            # 1) Allocate and apply
            for inv in invoices:
                if remaining <= 0:
                    break
                balance = inv.amount_due - inv.amount_paid
                if balance <= 0:
                    continue
                pay_now = min(balance, remaining)
                if pay_now <= 0:
                    continue

                # Your domain method: increments inv.amount_paid and sets status if fully paid
                inv.pay(pay_now)
                allocations.append((inv, pay_now))
                remaining -= pay_now

            # sanity: nothing applied?
            if not allocations:
                messages.error(request, "Nothing to apply. Please re-check invoices/amount.")
                transaction.set_rollback(True)
                return self.get(request, *args, **kwargs)

            # 2) Create Payment rows with the exact applied amounts
            paid_on_val = form.cleaned_data['paid_on'] or timezone.now()
            for inv, paid_amt in allocations:
                payments.append(
                    Payment.objects.create(
                        school=request.user.school,
                        invoice=inv,
                        amount=paid_amt,                        # ✅ exact allocation
                        method=form.cleaned_data['method'],
                        reference=form.cleaned_data.get('reference', ''),
                        paid_on=paid_on_val,
                    )
                )

            # 3) Update student's global payment_status
            if not student.invoices.filter(
                status__in=['UNPAID', 'OPENING_BALANCE']
            ).exists():
                student.payment_status = 'PAID'
            else:
                student.payment_status = 'UNPAID'
            student.save()

        # 4) Redirect back to Payment Detail. If receipts requested, add a signed token.
        messages.success(request, "Payment recorded successfully.")

        url = reverse_lazy('fees:payment_detail', kwargs={'pk': student.pk})

        if receipt_type in {"single", "separate"}:
            token = make_receipt_token(payments, request.user.school_id)

            # pass mode & token via query; page can show a banner with download buttons
            return redirect(f"{url}?rt={receipt_type}&receipt={token}")

        # 'none' → just go back to the page
        return redirect(url)


class InvoiceCreateView(RoleRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "fees/invoice_form.html"
    success_url = reverse_lazy("fees:invoices_list")
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN"]

    def form_valid(self, form):
        # Attach school automatically
        form.instance.school = self.request.user.school
        return super().form_valid(form)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "title": "Create Invoice",
            "subtitle": "Generate a new invoice for a student",
            "active_tab": "invoices",
        })
        return context


# ----------------------
# UPDATE INVOICE VIEW
# ----------------------
class InvoiceUpdateView(RoleRequiredMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "fees/invoice_form.html"
    success_url = reverse_lazy("fees:invoices_list")
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN"]

    def get_queryset(self):
        return Invoice.objects.filter(school=self.request.user.school)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "title": "Edit Invoice",
            "subtitle": "Update invoice details",
            "active_tab": "invoices",
        })
        return context
    
class InvoiceDeleteView(RoleRequiredMixin, DeleteView):
    model = Invoice
    template_name = "fees/invoice_confirm_delete.html"
    success_url = reverse_lazy("fees:invoices_list")
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN"]

    def get_queryset(self):
        return Invoice.objects.filter(school=self.request.user.school)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "title": "Delete Invoice",
            "subtitle": "Are you sure you want to delete this invoice?",
            "active_tab": "invoices",

        })
        return context

# ---------------- Payments ----------------
class PaymentListView(RoleRequiredMixin, ListView):
    model = Student
    template_name = "fees/payment_list.html"
    context_object_name = "students"
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN", "ACCOUNTANT"]
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        qs = Student.objects.filter(school=user.school, invoices__payments__isnull=False).annotate(
            total_paid=Sum(
                "invoices__payments__amount",
                filter=Q(invoices__school=user.school,invoices__payments__is_reversed = False)
            ),
            payments_count=Count(
                "invoices__payments",
                filter=Q(invoices__school=user.school)
            ),
            last_payment=Max(
                "invoices__payments__paid_on",
                filter=Q(invoices__school=user.school)
            ),
        )

        # Filter for parents
        if user.role == "PARENT":
            qs = qs.filter(parent=user)

        # Search
        search_query = self.request.GET.get("search", "").strip()
        if search_query:
            qs = qs.filter(
                Q(full_name__icontains=search_query) |
                Q(invoices__payments__reference__icontains=search_query)
            )

        return qs.order_by("-last_payment")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "search_query": self.request.GET.get("search", ""),
            "title": "Payments",
            "subtitle": "View and manage all student payments",
            "add_payment_url": reverse_lazy("fees:add_payment"),
            "add_payment_text": "+ Add Payment",
            "active_tab": "payments",
            "export_all": True
        })
        return context
    
class PaymentDetailView(RoleRequiredMixin, DetailView):
    model = Student
    template_name = "fees/payment_detail.html"
    context_object_name = "student"
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN", "ACCOUNTANT"]
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        return Student.objects.filter(
            school=user.school
        ).prefetch_related(
            Prefetch(
                'invoices',
                queryset=Invoice.objects.select_related('fee').prefetch_related('payments')
            ),
            Prefetch(
                'invoices__payments',
                queryset=Payment.objects.filter(is_reversed=False)
            )
        )
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.get_object()
        request = self.request

        # Start with only paid payments for this student
        payments = Payment.objects.filter(
            invoice__student=student, is_reversed = False
        ).select_related("invoice", "invoice__fee")
        reversals = PaymentReversal.objects.filter(payment__invoice__student = student ).select_related("payment", "reversed_by").order_by("-reversed_on")


        # 🔍 Search by reference
        search = request.GET.get("search")
        if search:
            payments = payments.filter(reference__icontains=search)

        # 🏷️ Filter by payment method
        method = request.GET.get("method")
        if method:
            payments = payments.filter(method=method)

        # 🏷️ Filter by fee type
        fee_type = request.GET.get("fee_type")
        if fee_type:
            payments = payments.filter(invoice__fee_id=fee_type)

        # 📅 Date range filter
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            payments = payments.filter(paid_on__date__gte=start_date)
        if end_date:
            payments = payments.filter(paid_on__date__lte=end_date)

        # 🧾 Summary info
        total_paid = payments.aggregate(total=Sum("amount"))["total"] or 0
        last_payment = payments.aggregate(last=Max("paid_on"))["last"]
        invoices = Invoice.objects.filter(student=student, status__in = ['UNPAID', "OPENING_BALANCE"])
        print(invoices)
        total_unpaid = invoices.aggregate(total=Sum("amount_due"))["total"] or 0

        # Dropdown filter data
        fee_types = FeeStructure.objects.filter(
            invoices__student=student
        ).distinct()

        payment_methods = Payment.objects.values_list("method", flat=True).distinct()
        paginator = Paginator(payments.order_by("-paid_on"), self.paginate_by)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        context.update({
        "payments": payments.order_by("-paid_on"),
            "total_paid": total_paid,
            "total_unpaid": total_unpaid,
            "last_payment": last_payment,
            "fee_types": fee_types,
            "payment_methods": payment_methods,
            "today": now().date(),
            "title": f"{student.full_name} Payments",
            "subtitle": "Payment history for this student",
            "add_url": reverse_lazy("fees:payments_list"),
            "add_button_text": "Back to Payment",
            "active_tab": "payments",
            "reversals": reversals,
            "invoice_detail_url": reverse_lazy("fees:invoice_detail", kwargs={"pk": student.pk}),
             "payments": page_obj,  # 👈 Use page_obj in template
            "page_obj": page_obj,
            "is_paginated": page_obj.has_other_pages(),
        })
        return context
# ---------------- Record Payment ----------------

class GenerateInvoicesView(RoleRequiredMixin, View):
    allowed_roles = ["ADMIN", "SCHOOL_ADMIN", "ACCOUNTANT"]
    success_url = reverse_lazy("fees:invoices_list")

    def post(self, request, *args, **kwargs):
        school = getattr(request.user, "school", None)
        if not school:
            messages.error(request, "❌ You must belong to a school to generate invoices.")
            return redirect(self.success_url)

        count = generate_invoices_for_school(school)
        if count > 0:
            messages.success(request, f"✅ Generated {count} invoice(s).")
        else:
            messages.info(request, "ℹ️ No invoices were generated.")
        return redirect(self.success_url)


from django.shortcuts import get_object_or_404, redirect
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Student, Invoice, Payment
from .forms import PaymentForm

class ExportInvoicesView(View):
    def get(self, request, *args, **kwargs):
        qs = Invoice.objects.filter(school=request.user.school)
        return export_invoices_to_excel(qs)

class ExportPaymentReceiptView(View):
    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, invoice__school=request.user.school)
        return export_payment_receipt_pdf(payment)

class BulkExportView(View):
    def get(self, request, *args, **kwargs):
        ids = request.GET.getlist("ids")
        export_type = request.GET.get("export_type", "excel")
        qs = Student.objects.filter(id__in=ids, school=request.user.school)

        if export_type == "pdf":
            return export_students_to_pdf(qs)
        return export_students_to_excel(qs)

class ExportStudentInvoicesExcelView(View):
    def get(self, request, pk, *args, **kwargs):
        student = get_object_or_404(Student, pk=pk, school=request.user.school)
        return export_student_invoices_to_excel(student)


class ExportStudentInvoicesPDFView(View):
    def get(self, request, pk, *args, **kwargs):
        student = get_object_or_404(Student, pk=pk, school=request.user.school)
        return export_student_invoices_to_pdf(student)


#Reverse the payment record
class ReversePaymentView(FormView):
    template_name = "fees/reverse_payment.html"
    form_class = PaymentReversalForm

    def dispatch(self, request, *args, **kwargs):
        self.payment = get_object_or_404(Payment, pk=kwargs['pk'])
        self.student = self.payment.invoice.student
        payment = self.payment 
        if self.payment.is_reversed:
            messages.error(request, '❌ This payment has already been reversed.')
        return super().dispatch(request, *args, **kwargs)
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["payment"] = self.payment
        context["student"] = self.student
        return context

    def form_valid(self, form):
        reason = form.cleaned_data['reason_choice']
        custom = form.cleaned_data['custom_reason']

        # Create reversal log
        PaymentReversal.objects.create(
            payment=self.payment,
            reversed_by=self.request.user,
            reason=reason if reason != "Other" else custom,
        
        )

        # Reverse invoice changes
        invoice = self.payment.invoice
        payment = self.payment
        invoice.amount_paid -= self.payment.amount
   

        if invoice.description != "Opening Balance":
            invoice.status = "UNPAID"
        else:
            invoice.status = 'OPENING_BALANCE'
        invoice.save()

        # Soft delete payment
        self.payment.is_reversed = True
        self.payment.save()

        messages.success(self.request, f"Payment #{self.payment.id} has been reversed.")
        return redirect('fees:payment_detail', pk=self.payment.invoice.student.pk)


from django.views import View
from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.core import signing

class ReceiptBundleDownloadView(View):
    def get(self, request):
        token = request.GET.get('t')
        mode = request.GET.get('mode', 'single')

        if not token:
            return HttpResponseBadRequest("Missing token.")

        try:
            data = signing.loads(token, max_age=RECEIPT_TOKEN_MAX_AGE)
        except signing.BadSignature:
            return HttpResponseBadRequest("Invalid token.")
        except signing.SignatureExpired:
            return HttpResponseBadRequest("Token expired.")

        payment_ids = data.get('p', [])
        school_id = data.get('s')

        qs = (Payment.objects
              .filter(id__in=payment_ids, school_id=school_id, is_reversed=False)
              .select_related('invoice__student', 'invoice__fee'))

        payments = list(qs)
        if not payments:
            return HttpResponseNotFound("No payments found.")

        if mode == 'single':
            return export_multiple_payment_receipts_pdf(payments)
        elif mode == 'separate':
            return export_separate_payment_receipts_zip(payments)
        else:
            return HttpResponseBadRequest("Unknown mode.")

class PaymentCreateView(FormView):
    model = Payment
    form_class = PaymentForm
    template_name = 'fees/payment_create.html'

    def get_object(self):
        # You can get the student using the ID passed in the URL
        student_id = self.kwargs.get('student_id')
        return get_object_or_404(Student, pk=student_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.get_object()
        invoices = student.invoices.filter(status='UNPAID')
        
        context.update({
            'student': student,
            'invoices': invoices,
            'total_unpaid': sum(invoice.amount_due - invoice.amount_paid for invoice in invoices),
        })
        return context

    def form_valid(self, form):
        student = self.get_object()
        invoices = student.invoices.filter(status='UNPAID').order_by('due_date')
        
        total_amount = form.cleaned_data['amount']
        if total_amount > sum(invoice.amount_due - invoice.amount_paid for invoice in invoices):
            form.add_error('amount', "The amount exceeds the total due for selected invoices.")
            return self.form_invalid(form)

        remaining_amount = total_amount
        for invoice in invoices:
            if remaining_amount <= 0:
                break

            balance_due = invoice.amount_due - invoice.amount_paid
            if remaining_amount >= balance_due:
                invoice.pay(balance_due)  # Mark invoice as fully paid
                remaining_amount -= balance_due
            else:
                invoice.pay(remaining_amount)  # Pay as much as possible
                remaining_amount = 0

        # Check if student has all invoices paid
        if all(invoice.status == 'PAID' for invoice in invoices):
            student.payment_status = 'PAID'
            student.save()

        # Record the payment
        payment = form.save(commit=False)
        payment.school = student.school  # Attach to the school of the student
        payment.save()

        messages.success(self.request, "Payment recorded successfully.")
        return redirect(reverse_lazy('fees:invoices_list'))  # Redirect after successful payment

    def form_invalid(self, form):
        messages.error(self.request, "There was an error processing your payment.")
        return super().form_invalid(form)
    
    
from django.http import HttpResponse
import openpyxl
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
from .models import Payment

def export_payments(request, pk):
    payment_ids = request.GET.getlist('payments')
    export_type = request.GET.get('export_type')

    payments = Payment.objects.filter(id__in=payment_ids) if payment_ids else Payment.objects.filter(student_id=pk)

    if export_type == 'pdf':
        return _export_payments_pdf(payments)
    elif export_type == 'excel':
        return _export_payments_excel(payments)

    return HttpResponse("Invalid export type", status=400)


def _export_payments_pdf(payments):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Payments Report")
    y -= 30

    p.setFont("Helvetica", 10)
    for payment in payments:
        p.drawString(50, y, f"{payment.paid_on} - {payment.invoice.fee.name} - {payment.amount} Br - {payment.method}")
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')


def _export_payments_excel(payments):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Payments"
    headers = ["Date", "Fee Type", "Amount", "Method", "Reference"]
    ws.append(headers)

    for payment in payments:
        ws.append([
            payment.paid_on.strftime('%Y-%m-%d'),
            payment.invoice.fee.name,
            payment.amount,
            payment.method,
            payment.reference or ''
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=payments.xlsx'
    wb.save(response)
    return response


class PaymentExportView(View):
    """
    Export selected or all payments as PDF or Excel.
    """

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get("export_type")
        selected_ids = request.GET.getlist("payments")

        if selected_ids:
            payments = Payment.objects.filter(id__in=selected_ids)
        else:
            payments = Payment.objects.all()

        if not payments.exists():
            return HttpResponse("No payments found.", status=404)

        if export_type in ["pdf", "pdf_all"]:
            return generate_payments_pdf(payments)
        elif export_type in ["excel", "excel_all"]:
            return generate_payments_excel(payments)

        return HttpResponse("Invalid export type.", status=400)