# fees/urls.py
from django.urls import path
from . import views
from .views import (
    FeesDashboardView,
    FeeListView, FeeCreateView, FeeUpdateView, FeeDeleteView,
    InvoiceListView, InvoiceDetailView,
    PaymentListView, InvoiceCreateView, InvoiceUpdateView, InvoiceDeleteView, GenerateInvoicesView, PaymentDetailView, ExportStudentInvoicesExcelView, ExportStudentInvoicesPDFView, ReversePaymentView, ReceiptBundleDownloadView, PaymentExportView
)

app_name = "fees"

urlpatterns = [
    # Dashboard
    path('', FeesDashboardView.as_view(), name='fee-dashboard'),

    # Fee Setup
    path('fees/', FeeListView.as_view(), name='fees_list'),
    path('fees/add/', FeeCreateView.as_view(), name='add_fee'),
    path('fees/<int:pk>/edit/', FeeUpdateView.as_view(), name='edit_fee'),
    path('fees/<int:pk>/delete/', FeeDeleteView.as_view(), name='delete_fee'),

    # Invoices
    path('invoices/', InvoiceListView.as_view(), name='invoices_list'),
    path("invoices/<int:pk>/", InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/create/", InvoiceCreateView.as_view(), name="create_invoice"),
    path("invoices/<int:pk>/edit/", InvoiceUpdateView.as_view(), name="edit_invoice"),
    path("invoices/<int:pk>/delete/", InvoiceDeleteView.as_view(), name="delete_invoice"),
    path("invoices/generate/", GenerateInvoicesView.as_view(), name="invoice_generate"),

    # Payments
    path('payments/', PaymentListView.as_view(), name='payments_list'),
    path(
    "students/<int:pk>/payments/",
    PaymentDetailView.as_view(),
    name="payment_detail",
),
    
    #Export
   path("students/<int:pk>/export/invoices/excel/", ExportStudentInvoicesExcelView.as_view(), name="export_student_invoices_excel"),
   path("students/<int:pk>/export/invoices/pdf/", ExportStudentInvoicesPDFView.as_view(), name="export_student_invoices_pdf"),
path("receipts/download/", ReceiptBundleDownloadView.as_view(), name="fees_download_receipts"),

   #Undo
path('payments/<int:pk>/reverse/', ReversePaymentView.as_view(), name='reverse_payment'),
path('students/<int:pk>/export-payments/', views.export_payments, name='export_payments'),
# fees/urls.py
path("payments/export/", PaymentExportView.as_view(), name="export_payments"),


]
