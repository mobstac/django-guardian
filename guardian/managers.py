from __future__ import unicode_literals

from django.core.cache import cache
from django.db import models
from django.contrib.contenttypes.models import ContentType

from guardian.compat import get_user_model
from guardian.core import ObjectPermissionChecker
from guardian.exceptions import ObjectNotPersisted
from guardian.models import Permission
import warnings

# TODO: consolidate UserObjectPermissionManager and GroupObjectPermissionManager

class BaseObjectPermissionManager(models.Manager):

    def is_generic(self):
        try:
            self.model._meta.get_field('object_pk')
            return True
        except models.fields.FieldDoesNotExist:
            return False


class UserObjectPermissionManager(BaseObjectPermissionManager):

    def assign_perm(self, perm, user, obj):
        """
        Assigns permission with given ``perm`` for an instance ``obj`` and
        ``user``.
        """
        if getattr(obj, 'pk', None) is None:
            raise ObjectNotPersisted("Object %s needs to be persisted first"
                % obj)
        ctype = ContentType.objects.get_for_model(obj)
        permission = Permission.objects.get(content_type=ctype, codename=perm)

        kwargs = {'permission': permission, 'user': user}
        if self.is_generic():
            kwargs['content_type'] = ctype
            kwargs['object_pk'] = obj.pk
        else:
            kwargs['content_object'] = obj
        obj_perm, created = self.get_or_create(**kwargs)

        # Add to cache
        check = ObjectPermissionChecker(user)
        key = check.get_local_cache_key(obj)
        cache_perms = cache.get(key)
        if cache_perms is not None and perm not in cache_perms:
            cache_perms.append(perm)
            cache.set(key, cache_perms)

        return obj_perm

    def assign(self, perm, user, obj):
        """ Depreciated function name left in for compatibility"""
        warnings.warn("UserObjectPermissionManager method 'assign' is being renamed to 'assign_perm'. Update your code accordingly as old name will be depreciated in 1.0.5 version.", DeprecationWarning)
        return self.assign_perm(perm, user, obj)

    def remove_perm(self, perm, user, obj):
        """
        Removes permission ``perm`` for an instance ``obj`` and given ``user``.

        Please note that we do NOT fetch object permission from database - we
        use ``Queryset.delete`` method for removing it. Main implication of this
        is that ``post_delete`` signals would NOT be fired.
        """
        if getattr(obj, 'pk', None) is None:
            raise ObjectNotPersisted("Object %s needs to be persisted first"
                % obj)
        filters = {
            'permission__codename': perm,
            'permission__content_type': ContentType.objects.get_for_model(obj),
            'user': user,
        }
        if self.is_generic():
            filters['object_pk'] = obj.pk
        else:
            filters['content_object__pk'] = obj.pk
        self.filter(**filters).delete()

        #Remove for cache
        check = ObjectPermissionChecker(user)
        key = check.get_local_cache_key(obj)
        cache_perms = cache.get(key)
        if cache_perms is not None and perm in cache_perms:
            cache_index = 0
            for cache_perm in cache_perms:
                if perm == cache_perm:
                    cache_perms.pop(cache_index)
                    break
                cache_index += 1
            cache.set(key, cache_perms)


    def get_for_object(self, user, obj):
        if getattr(obj, 'pk', None) is None:
            raise ObjectNotPersisted("Object %s needs to be persisted first"
                % obj)
        ctype = ContentType.objects.get_for_model(obj)
        perms = self.filter(
            content_type = ctype,
            user = user,
        )
        return perms


class GroupObjectPermissionManager(BaseObjectPermissionManager):

    def assign_perm(self, perm, group, obj):
        """
        Assigns permission with given ``perm`` for an instance ``obj`` and
        ``group``.
        """
        if getattr(obj, 'pk', None) is None:
            raise ObjectNotPersisted("Object %s needs to be persisted first"
                % obj)
        ctype = ContentType.objects.get_for_model(obj)
        permission = Permission.objects.get(content_type=ctype, codename=perm)

        kwargs = {'permission': permission, 'group': group}
        if self.is_generic():
            kwargs['content_type'] = ctype
            kwargs['object_pk'] = obj.pk
        else:
            kwargs['content_object'] = obj
        obj_perm, created = self.get_or_create(**kwargs)

        # Add to cache
        check = ObjectPermissionChecker(group)
        key = check.get_local_cache_key(obj)
        cache_perms = cache.get(key)
        if cache_perms is not None and perm not in cache_perms:
            cache_perms.append(perm)
            cache.set(key, cache_perms)

        User = get_user_model()
        users = User.objects.filter(groups = group)
        for user in users:
            check = ObjectPermissionChecker(user)
            key = check.get_local_cache_key(obj)
            cache.delete(key)

        return obj_perm

    def assign(self, perm, user, obj):
        """ Depreciated function name left in for compatibility"""
        warnings.warn("UserObjectPermissionManager method 'assign' is being renamed to 'assign_perm'. Update your code accordingly as old name will be depreciated in 1.0.5 version.", DeprecationWarning)
        return self.assign_perm(perm, user, obj)

    def remove_perm(self, perm, group, obj):
        """
        Removes permission ``perm`` for an instance ``obj`` and given ``group``.
        """
        if getattr(obj, 'pk', None) is None:
            raise ObjectNotPersisted("Object %s needs to be persisted first"
                % obj)
        filters = {
            'permission__codename': perm,
            'permission__content_type': ContentType.objects.get_for_model(obj),
            'group': group,
        }
        if self.is_generic():
            filters['object_pk'] = obj.pk
        else:
            filters['content_object__pk'] = obj.pk

        self.filter(**filters).delete()

        #Remove for cache
        check = ObjectPermissionChecker(group)
        key = check.get_local_cache_key(obj)
        cache_perms = cache.get(key)
        if cache_perms is not None and perm in cache_perms:
            cache_index = 0
            for cache_perm in cache_perms:
                if perm == cache_perm:
                    cache_perms.pop(cache_index)
                    break
                cache_index += 1
            cache.set(key, cache_perms)

        User = get_user_model()
        users = User.objects.filter(groups = group)
        for user in users:
            check = ObjectPermissionChecker(user)
            key = check.get_local_cache_key(obj)
            cache.delete(key)
        
    def get_for_object(self, group, obj):
        if getattr(obj, 'pk', None) is None:
            raise ObjectNotPersisted("Object %s needs to be persisted first"
                % obj)
        ctype = ContentType.objects.get_for_model(obj)
        perms = self.filter(
            content_type = ctype,
            group = group,
        )
        return perms

