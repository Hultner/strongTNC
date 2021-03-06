# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import, unicode_literals

from django.db import transaction
from django.core.exceptions import ValidationError

from lxml import etree

from apps.filesystem.models import Directory, File
from apps.swid.models import Entity, EntityRole, TagStats
from .models import Tag


class SwidParser(object):
    """
    A SAX-like target parser for SWID XML files.
    """

    def __init__(self):
        self.tag = Tag()
        self.entities = []
        self.files = []

    def start(self, tag, attrib):
        """
        Fired on element open. The data and children of the element are not yet
        available.
        """
        clean_tag = tag.split('}')[-1]  # Strip XSD part from tag name
        if clean_tag == 'SoftwareIdentity':
            # Store basic attributes
            self.tag.package_name = attrib['name']
            self.tag.unique_id = attrib['uniqueId']
            self.tag.version = attrib['version']
        elif clean_tag == 'File':
            # Store directories and files
            dirname = attrib['location']
            filename = attrib['name']
            d, _ = Directory.objects.get_or_create(path=dirname)
            f, _ = File.objects.get_or_create(name=filename, directory=d)
            self.files.append(f)
        elif clean_tag == 'Entity':
            # Store entities
            regid = attrib['regid']
            name = attrib['name']
            roles = attrib['role']
            for role in roles.split():
                entity, _ = Entity.objects.get_or_create(regid=regid)
                entity.name = name

                role_id = EntityRole.xml_attr_to_choice(role)
                entity_role = EntityRole()
                entity_role.role = role_id
                self.entities.append((entity, entity_role))

                # Use regid of last entity with tagcreator role to construct software-id
                if role_id == EntityRole.TAGCREATOR:
                    self.tag.software_id = '%s_%s' % (regid, self.tag.unique_id)

    def close(self):
        """
        Fired when parsing is complete.
        """
        if not self.tag.software_id:
            msg = 'A SWID tag (%s) without a `tagcreator` entity is currently not supported.'
            raise ValueError(msg % self.tag.unique_id)
        return self.tag, self.files, self.entities


@transaction.atomic
def process_swid_tag(tag_xml, allow_tag_update=False):
    """
    Parse a SWID XML tag and store the contained elements in the database.

    The tag must be a unicode object in order to be processed correctly.

    All database changes run in a transaction. When an error occurs, the
    database remains unchanged.

    Args:
       tag_xml (unicode):
           The SWID tag as an XML string.
       allow_tag_update (bool):
            If the tag already exists its data gets overwritten.

    Returns:
       A tuple containing the newly created Tag model instance and a flag
       whether a pre-existing tag was replaced or not.

    """
    # Instantiate parser
    parser_target = SwidParser()
    parser = etree.XMLParser(target=parser_target, ns_clean=True)

    # Parse XML, save tag into database
    try:
        tag, files, entities = etree.fromstring(tag_xml.encode('utf8'), parser)
    except KeyError as ke:
        raise ValueError('Invalid tag: missing %s property' % ke.message)

    tag.swid_xml = prettify_xml(tag_xml)

    # Check whether tag already exists
    try:
        old_tag = Tag.objects.get(software_id=tag.software_id)
    # Tag doesn't exist, create a new one later on
    except Tag.DoesNotExist:
        replaced = False
    # Tag exists already
    else:
        # Tag already exists but updates are not allowed
        if not allow_tag_update:
            replaced = False
            # The tag will not be changed, but we want to make sure
            # that the entities have the right name.
            for entity, _ in entities:
                Entity.objects.filter(pk=entity.pk).update(name=entity.name)

            # Tag needs to be reloaded after entity updates
            return Tag.objects.get(pk=old_tag.pk), replaced
        # Update tag with new information
        old_tag.package_name = tag.package_name
        old_tag.version = tag.version
        old_tag.unique_id = tag.unique_id
        old_tag.files.clear()
        chunked_bulk_add(old_tag.files, files, 980)
        old_tag.swid_xml = tag.swid_xml
        tag = old_tag
        tag.entity_set.clear()
        replaced = True

    # Validate and save tag and entity
    try:
        tag.full_clean()
        tag.save()  # We need to save before we can add many-to-many relations

        # Add entities
        for entity, entity_role in entities:
            entity.full_clean()
            entity.save()
            entity_role.tag = tag
            entity_role.entity = entity
            entity_role.full_clean()
            entity_role.save()
    except ValidationError as e:
        msgs = []
        for field, errors in e.error_dict.iteritems():
            error_str = ' '.join([m for err in errors for m in err.messages])
            msgs.append('%s: %s' % (field, error_str))
        raise ValueError(' '.join(msgs))

    # SQLite does not support >999 SQL parameters per query, so we need
    # to do manual chunking.
    chunked_bulk_add(tag.files, files, 980)

    return tag, replaced


def prettify_xml(xml, xml_declaration=True):
    """
    Create a correctly indented (pretty) XML string from a parsable XML input.

    Args:
        xml (unicode):
            The XML string to be prettified
        xml_declaration (bool):
            Wheter a XML declaration should be added or not.
            Recommended for standalone documents.

    Returns:
        A prettified version of the given XML string.

    """
    xml_bytes = xml.encode('utf8')
    return etree.tostring(etree.fromstring(xml_bytes),
                          pretty_print=True,
                          xml_declaration=xml_declaration,
                          encoding='UTF-8')


def chunked_bulk_add(manager, objects, block_size):
    """
    Add items to a reverse FK relation in chunks.

    Args:
        manager:
            The target model manager.
        objects:
            The objects to add to the target model.
        block_size:
            Number of objects per block.

    """
    for i in xrange(0, len(objects), block_size):
        pk_slice = objects[i:i + block_size]
        manager.add(*pk_slice)


def chunked_filter_in(queryset, filter_field, filter_list, block_size):
    """
    Select items from an ``field__in=filter_list`` filtered queryset in
    multiple queries.

    Example: If you have the following query ::

        SELECT * FROM items WHERE id IN (1, 2, 3, 4, 5, 6);

    ...and you want to do a chunked filtering with block size 2, the result is
    that the following queries are executed::

        SELECT * FROM items WHERE id IN (1, 2);
        SELECT * FROM items WHERE id IN (3, 4);
        SELECT * FROM items WHERE id IN (5, 6);

    Args:
        queryset:
            The base queryset.
        filter_field:
            The field to filter on.
        filter_list:
            The list of values for the ``IN`` filtering. This is the list that
            will be chunked.
        block_size:
            The number of items to filter by per query.

    Returns:
        Return a list containing all the items from all the querysets.

    """
    out = []
    for i in xrange(0, len(filter_list), block_size):
        filter_slice = filter_list[i:i + block_size]
        kwargs = {filter_field + '__in': filter_slice}
        items = list(queryset.filter(**kwargs))
        out.extend(items)
    return out


def update_tag_stats(session, tag_ids):
    new_tags = []
    block_size = 980
    for i in xrange(0, len(tag_ids), block_size):
        tag_ids_slice = tag_ids[i:i + block_size]
        # TODO: Instead of filtering the device tags, a list of all tags for a
        # device could be created outside of the loop.
        existing_tags = TagStats.objects.filter(device__pk=session.device_id,
                                                tag__pk__in=tag_ids_slice)
        new_tags.extend(set(tag_ids_slice) - set(existing_tags.values_list('tag__pk', flat=True)))
        existing_tags.update(last_seen=session)

    # Chunked create is done by default for sqlite,
    # see https://docs.djangoproject.com/en/dev/ref/models/querysets/#bulk-create
    TagStats.objects.bulk_create([
        TagStats(tag_id=t, device=session.device, first_seen=session, last_seen=session)
        for t in new_tags]
    )
