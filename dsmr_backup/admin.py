from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.forms import TextInput
from django.utils import timezone
from django.contrib import admin
from django.conf import settings
from django.db import models
from solo.admin import SingletonModelAdmin
import django.db.models.signals

from dsmr_backup.forms import BackupSettingsAdminForm
from .models.settings import BackupSettings, DropboxSettings, EmailBackupSettings
from dsmr_backend.models.settings import EmailSettings
from dsmr_backend.models.schedule import ScheduledProcess


@admin.register(BackupSettings)
class BackupSettingsAdmin(SingletonModelAdmin):
    change_form_template = 'dsmr_backup/backup_settings/change_form.html'
    form = BackupSettingsAdminForm
    readonly_fields = ('latest_backup', )
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '64'})},
    }
    fieldsets = (
        (
            None, {
                'fields': ['daily_backup', 'backup_time'],
                'description': _(
                    'Detailed instructions for restoring a backup can be found here: <a href="https://dsmr-reader.readt'
                    'hedocs.io/nl/v2/faq.html#how-do-i-restore-a-database-backup">FAQ in documentation</a>.'
                )
            }
        ),
        (
            _('Advanced'), {
                'fields': ['folder'],
            }
        ),
        (
            _('Automatic fields'), {
                'fields': ['latest_backup']
            }
        ),
    )

    def response_change(self, request, obj):
        BackupSettings.objects.all().update(latest_backup=None)
        return super(BackupSettingsAdmin, self).response_change(request, obj)


@admin.register(DropboxSettings)
class DropboxSettingsAdmin(SingletonModelAdmin):
    change_form_template = 'dsmr_backup/dropbox_settings/change_form.html'
    readonly_fields = ('latest_sync', 'next_sync')
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '64'})},
    }
    fieldsets = (
        (
            None, {
                'fields': ['access_token'],
                'description': _(
                    'This will synchronize backups to your Dropbox account. Detailed instructions for configuring '
                    'Dropbox can be found here: <a href="https://dsmr-reader.readthedocs.io/nl/v2/admin/'
                    'backup_dropbox.html">Documentation</a>'
                )
            }
        ),
        (
            _('Automatic fields'), {
                'fields': ['latest_sync', 'next_sync']
            }
        ),
    )

    def response_change(self, request, obj):
        DropboxSettings.objects.all().update(next_sync=timezone.now())
        return super(DropboxSettingsAdmin, self).response_change(request, obj)


@admin.register(EmailBackupSettings)
class EmailBackupSettingsAdmin(SingletonModelAdmin):
    change_form_template = 'dsmr_backup/email_backup_settings/change_form.html'
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size': '64'})},
    }
    fieldsets = (
        (
            None, {
                'fields': ['interval'],
                'description': _(
                    'You can have DSMR-reader email you a backup every once in a while.'
                    '<br><br>Please note that the backup will <strong>ONLY contain day and hour statistics</strong>, '
                    'which are the most important data to preserve historically.'
                )
            }
        ),
    )

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        context.update(dict(email_address=EmailSettings.get_solo().email_to))
        return super(EmailBackupSettingsAdmin, self).render_change_form(
            request, context, add, change, form_url, obj
        )

    def response_change(self, request, obj):
        ScheduledProcess.objects.filter(
            module=settings.DSMRREADER_MODULE_EMAIL_BACKUP
        ).update(planned=timezone.now())
        return super(EmailBackupSettingsAdmin, self).response_change(request, obj)


@receiver(django.db.models.signals.post_save, sender=EmailBackupSettings)
def handle_email_backup_settings_update(sender, instance, **kwargs):
    """ Hook to toggle related scheduled process. """
    ScheduledProcess.objects.filter(
        module=settings.DSMRREADER_MODULE_EMAIL_BACKUP
    ).update(active=instance.interval != EmailBackupSettings.INTERVAL_NONE)
