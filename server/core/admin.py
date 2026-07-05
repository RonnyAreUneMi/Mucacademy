from django.contrib import admin, messages
from core.models import (
    User, AccessRequest, Event, Attendance,
    Enrollment, SessionSummary, QuizAttempt,
)


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'participant', 'event', 'correct', 'total', 'percentage', 'total_time_seconds', 'created_at')
    list_filter = ('event', 'created_at')
    search_fields = ('participant__email', 'participant__national_id', 'event__title')
    readonly_fields = ('created_at', 'percentage')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'get_full_name', 'role', 'faculty', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = (
        ('Personal info', {'fields': ('username', 'email', 'first_name', 'last_name', 'phone')}),
        ('Institution', {'fields': ('faculty', 'role')}),
        ('Status', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    readonly_fields = ('date_joined', 'last_login')


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ('get_requester', 'email', 'status', 'requested_at')
    list_filter = ('status', 'requested_at', 'faculty')
    search_fields = ('first_name', 'last_name', 'email')
    readonly_fields = ('requested_at', 'responded_at', 'created_user')
    fieldsets = (
        ('Request', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Institution', {'fields': ('faculty',)}),
        ('Response', {'fields': ('status', 'created_user', 'approved_by', 'rejection_reason', 'responded_at')}),
        ('Audit', {'fields': ('requested_at',), 'classes': ('collapse',)}),
    )

    def get_requester(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_requester.short_description = "Requester"

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['first_name', 'last_name', 'email', 'faculty']
        return self.readonly_fields


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'date', 'capacity', 'enrolled_count', 'is_active')
    list_filter = ('date', 'is_active', 'batch')
    search_fields = ('title', 'batch__name')
    readonly_fields = ('qr_code', 'enrolled_count', 'created_at')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('get_certificate_info', 'event', 'registered_at')
    list_filter = ('event__date', 'registered_at')
    search_fields = ('certificate__national_id', 'certificate__email')
    readonly_fields = ('registered_at',)

    def get_certificate_info(self, obj):
        c = obj.certificate
        if c:
            return f"{c.first_name} {c.last_name} ({c.national_id})"
        p = obj.participant
        return f"{p.first_name} {p.last_name}" if p else '?'
    get_certificate_info.short_description = "Participant"


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('get_person', 'event', 'confirmed', 'blocked')
    list_filter = ('confirmed', 'blocked', 'event__date')
    search_fields = ('participant__national_id', 'participant__email')
    actions = ['mark_blocked', 'unmark_blocked']

    def get_person(self, obj):
        p = obj.participant
        if p:
            return f"{p.first_name} {p.last_name}"
        c = obj.certificate
        return f"{c.first_name} {c.last_name}" if c else '?'
    get_person.short_description = "Participant"

    def mark_blocked(self, request, queryset):
        queryset.update(blocked=True)
    mark_blocked.short_description = "Mark as blocked"

    def unmark_blocked(self, request, queryset):
        queryset.update(blocked=False)
    unmark_blocked.short_description = "Unmark blocked"


@admin.register(SessionSummary)
class SessionSummaryAdmin(admin.ModelAdmin):
    list_display = (
        'event', 'status', 'transcript_chars', 'duration_minutes',
        'ai_model', 'processed_at', 'created_at',
    )
    list_filter = ('status', 'ai_model', 'created_at')
    search_fields = ('event__title', 'drive_file_name', 'drive_file_id')
    readonly_fields = (
        'created_at', 'processed_at',
        'transcript_chars', 'duration_minutes',
        'ai_input_tokens', 'ai_output_tokens',
    )
    actions = ['reprocess', 'clear_transcript_raw']

    fieldsets = (
        ('Event', {'fields': ('event', 'status', 'error_msg')}),
        ('Drive source', {'fields': (
            'drive_file_id', 'drive_file_name', 'transcript_chars',
        )}),
        ('AI result', {'fields': (
            'summary_md', 'key_points', 'next_steps', 'quiz',
            'duration_minutes',
        )}),
        ('Audit', {'fields': (
            'ai_model', 'ai_input_tokens', 'ai_output_tokens',
            'created_at', 'processed_at',
        )}),
        ('Raw transcript (may be large)', {
            'classes': ('collapse',),
            'fields': ('transcript_raw',),
        }),
    )

    def reprocess(self, request, queryset):
        from core.tasks.transcript_tasks import process_event_transcript
        queued = 0
        for summary in queryset:
            process_event_transcript.delay(summary.event_id)
            queued += 1
        self.message_user(
            request, f'Queued reprocessing of {queued} summary(ies).',
            level=messages.INFO,
        )
    reprocess.short_description = 'Reprocess transcript with AI'

    def clear_transcript_raw(self, request, queryset):
        """Free DB space by clearing raw text (keeps summary + quiz)."""
        n = 0
        for r in queryset:
            r.transcript_raw = ''
            r.save(update_fields=['transcript_raw'])
            n += 1
        self.message_user(
            request, f'Raw transcript cleared in {n} summary(ies).',
            level=messages.INFO,
        )
    clear_transcript_raw.short_description = 'Clear raw transcript (keeps summary)'
