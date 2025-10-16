# notifications/views.py
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, DeleteView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from core.mixins import RoleRequiredMixin, UserScopedMixin
from .models import Announcement, AnnouncementAttachment
from .forms import AnnouncementForm
from django.utils.dateparse import parse_date
from django.db.models import Q, Case, When, IntegerField, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.db.models import Exists, OuterRef


class AnnouncementCreateView(RoleRequiredMixin, UserScopedMixin, CreateView):
  model = Announcement
  form_class = AnnouncementForm
  template_name = 'notifications/create.html'
  success_url = reverse_lazy('notifications:list')
  allowed_roles = ['SCHOOL_ADMIN', 'TEACHER']
  
  def get_form_kwargs(self):
        """Pass the logged-in user to the form for scoping dropdowns."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  
        return kwargs

  def form_valid(self, form):
      form.instance.created_by = self.request.user
      form.instance.school = self.request.user.school
      # School is set by UserScopedMixin.form_valid()
      response = super().form_valid(form)
      files = self.request.FILES.getlist('attachments')
      with transaction.atomic():
          for f in files:
              AnnouncementAttachment.objects.create(
                  announcement=self.object,
                  file=f,
                  label=f.name
              )
      messages.success(self.request, '✅ Announcement created successfully!')
      return response

  def form_invalid(self, form):
    for field, errors in form.errors.items():
        for error in errors:
            if field == "__all__":
                messages.error(self.request, error)
            else:
                messages.error(self.request, f"{field.capitalize()}: {error}")
    return super().form_invalid(form)
class AnnouncementListView(RoleRequiredMixin, UserScopedMixin, ListView):
    model = Announcement
    template_name = 'notifications/list.html'
    context_object_name = 'announcements'
    allowed_roles = ['TEACHER', 'PARENT', 'SCHOOL_ADMIN']
    paginate_by = 10  # announcements per page

    def get_queryset(self):
        # Base queryset: active announcements targeted to user
        qs = super().get_queryset()
        qs = qs.active().targeted_to(self.request.user)

        # Annotate read status
        reads_subquery = AnnouncementRead.objects.filter(
            announcement=OuterRef('pk'),
            user=self.request.user
        )
        qs = qs.annotate(is_read=Exists(reads_subquery))

        # Annotate reactions and read counts
        qs = qs.annotate(
            likes_count=Count('reactions', filter=Q(reactions__reaction='LIKE')),
            loves_count=Count('reactions', filter=Q(reactions__reaction='LOVE')),
            acks_count=Count('reactions', filter=Q(reactions__reaction='ACK')),
            reads_count=Count('reads')
        )

        # Annotate numeric priority for ordering (pinned > urgent > important > info)
        qs = qs.annotate(
            priority_order=Case(
                When(pinned=True, then=4),           # pinned messages always top
                When(priority='URGENT', then=3),
                When(priority='IMPORTANT', then=2),
                When(priority='INFO', then=1),
                default=0,
                output_field=IntegerField()
            )
        )

        # Ordering: pinned -> unread -> priority -> newest
        qs = qs.order_by('-priority_order', '-is_read', '-publish_at')

        # Filters
        priority = self.request.GET.get("priority")
        channel  = self.request.GET.get("channel")
        start    = self.request.GET.get("start")
        end      = self.request.GET.get("end")
        search   = self.request.GET.get("search")
        category = self.request.GET.get("category")

        filters = Q()
        if priority:
            filters &= Q(priority=priority)
        if channel:
            filters &= Q(delivery_channels__icontains=channel)
        if start:
            d = parse_date(start)
            if d:
                filters &= Q(publish_at__date__gte=d)
        if end:
            d = parse_date(end)
            if d:
                filters &= Q(publish_at__date__lte=d)
        if search:
            filters &= Q(title__icontains=search) | Q(message__icontains=search)
        if category:
            filters &= Q(category=category)

        if filters:
            qs = qs.filter(filters)

        return qs
class AnnouncementUpdateView(LoginRequiredMixin, UpdateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = "notifications/create.html"  # reuse
    success_url = reverse_lazy("notifications:announcement_list")

    def get_queryset(self):
        # Limit editing to announcements in user's school
        return Announcement.objects.filter(school=self.request.user.school)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

class AnnouncementDeleteView(LoginRequiredMixin, DeleteView):
    model = Announcement
    template_name = "notifications/delete.html"
    success_url = reverse_lazy("notifications:list")

    def get_queryset(self):
        # Limit deletion to announcements in user's school
        return Announcement.objects.filter(school=self.request.user.school)
    

def announcements_page(request):
    """AJAX endpoint for 'Load more'."""
    page = int(request.GET.get("page", 1))
    qs = Announcement.objects.active().targeted_to(request.user)
    # apply same filters here too
    ...
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(page)
    html = render_to_string("notifications/_announcement_cards.html",
                            {"announcements": page_obj.object_list,
                             "request": request})
    return JsonResponse({
        "html": html,
        "has_next": page_obj.has_next(),
        "next_page": page + 1 if page_obj.has_next() else None
    })

# notifications/views.py
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

class AnnouncementAnalyticsView(RoleRequiredMixin, UserScopedMixin, TemplateView):
    template_name = 'notifications/analytics.html'
    allowed_roles = ['SCHOOL_ADMIN', 'TEACHER']

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Filters: date range + category scope
        rng = (self.request.GET.get("range") or "30d").lower()  # 7d, 30d, 90d, all
        scope_cat = self.request.GET.get("scope_category")  # optional

        base_qs = Announcement.objects.targeted_to(self.request.user).active()
        if scope_cat:
            base_qs = base_qs.filter(category=scope_cat)

        # Date window for trend
        if rng == "7d":
            start = timezone.now() - timedelta(days=7)
        elif rng == "90d":
            start = timezone.now() - timedelta(days=90)
        elif rng == "all":
            start = None
        else:
            start = timezone.now() - timedelta(days=30)

        trend_qs = base_qs
        if start:
            trend_qs = trend_qs.filter(publish_at__gte=start)

        # Summary KPIs
        ctx['stats'] = {
            'total': base_qs.count(),
            'pinned': base_qs.filter(pinned=True).count(),
            'urgent': base_qs.filter(priority='URGENT').count(),
            'reads': sum(a.reads.count() for a in base_qs),
            'reactions': sum(a.reactions.count() for a in base_qs),
        }

        # Breakdowns
        ctx['categories'] = (
            base_qs.values('category')
                   .annotate(count=Count('id'))
                   .order_by('-count')
        )
        ctx['priorities'] = (
            base_qs.values('priority')
                   .annotate(count=Count('id'))
                   .order_by('-count')
        )

        # Trend
        trend = (
            trend_qs.annotate(day=TruncDate('publish_at'))
                    .values('day')
                    .annotate(
                        reads=Count('reads', distinct=True),
                        reactions=Count('reactions', distinct=True),
                    )
                    .order_by('day')
        )
        ctx['trend'] = list(trend)

        # Recent
        ctx['recent'] = base_qs.order_by('-publish_at')[:10]

        # Pass filters back
        ctx['range'] = rng
        ctx['scope_category'] = scope_cat

        return ctx

# notifications/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Announcement, AnnouncementRead, AnnouncementReaction

@require_POST
@login_required
def mark_read(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    AnnouncementRead.objects.get_or_create(announcement=ann, user=request.user)
    return JsonResponse({"status": "ok", "reads": ann.reads.count()})

@require_POST
@login_required
def toggle_reaction(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    reaction_type = request.POST.get("reaction")
    if reaction_type not in dict(AnnouncementReaction._meta.get_field("reaction").choices):
        return JsonResponse({"status": "error", "msg": "Invalid reaction"}, status=400)

    obj, created = AnnouncementReaction.objects.get_or_create(
        announcement=ann, user=request.user, reaction=reaction_type
    )
    if not created:
        obj.delete()  # toggle off
    type_count = ann.reactions.filter(reaction=reaction_type).count()
    return JsonResponse({
        "status": "ok",
        "reaction_count": type_count,
        "type": reaction_type
    })

from django.contrib.auth.decorators import login_required

@login_required
def unread_count(request):
    count = Announcement.objects.unread_for(request.user).count()
    return JsonResponse({"count": count})
