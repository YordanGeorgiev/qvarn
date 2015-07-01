# write_only_tests.py - unit tests for WriteOnlyStorage
#
# Copyright 2015 Suomen Tilaajavastuu Oy
# All rights reserved.


import unittest

import unifiedapi


class WriteOnlyStorageTests(unittest.TestCase):

    prototype = {
        u'type': u'',
        u'id': u'',
        u'revision': u'',
        u'name': u'',
        u'aliases': [u''],
        u'addrs': [
            {
                u'country': u'',
                u'lines': [u''],
            }
        ],
    }

    person = {
        u'type': u'person',
        u'name': u'James Bond',
        u'aliases': [u'Alfred E. Newman'],
        u'addrs': [
            {
                u'country': u'FI',
                u'lines': [u'addr1', u'addr2'],
            },
            {
                u'country': u'GB',
                u'lines': [u'flim', u'flam'],
            },
        ],
    }

    subitem_name = u'secret'

    subitem_prototype = {
        u'secret_identity': u'',
    }

    def create_tables(self, db):
        db.create_table(
            u'person',
            (u'type', unicode),
            (u'id', unicode),
            (u'revision', unicode),
            (u'name', unicode))
        db.create_table(
            u'person_aliases',
            (u'id', unicode),
            (u'list_pos', int),
            (u'aliases', unicode))
        db.create_table(
            u'person_addrs',
            (u'id', unicode),
            (u'list_pos', int),
            (u'country', unicode))
        db.create_table(
            u'person_addrs_lines',
            (u'id', unicode),
            (u'dict_list_pos', int),
            (u'list_pos', int),
            (u'lines', unicode))
        db.create_table(
            u'person_secret',
            (u'id', unicode),
            (u'secret_identity', unicode))

    def setUp(self):
        db = unifiedapi.open_memory_database()

        prep = unifiedapi.StoragePreparer()
        prep.add_step(u'create', self.create_tables)
        self.wo = unifiedapi.WriteOnlyStorage()
        self.wo.set_db(db)
        self.wo.set_item_prototype(self.person[u'type'], self.prototype)
        self.wo.set_subitem_prototype(
            self.person[u'type'], self.subitem_name, self.subitem_prototype)
        self.wo.set_preparer(prep)
        self.wo.prepare()

        self.ro = unifiedapi.ReadOnlyStorage()
        self.ro.set_db(db)
        self.ro.set_item_prototype(self.person[u'type'], self.prototype)
        self.ro.set_subitem_prototype(
            self.person[u'type'], self.subitem_name, self.subitem_prototype)

    def test_adds_item_and_invents_id_and_revision(self):
        added = self.wo.add_item(self.person)

        self.assertIn('id', added)
        self.assertEqual(type(added[u'id']), unicode)

        self.assertIn('revision', added)
        self.assertEqual(type(added[u'revision']), unicode)

        self.assertEqual(
            sorted(self.person.keys() + [u'id', u'revision']),
            sorted(added.keys()))

        self.assertEqual(
            sorted(self.person.items()),
            sorted((k, v) for k, v in added.items()
                   if k not in [u'id', u'revision']))

        obj = self.get_item_from_disk(added)
        self.assertEqual(added, obj)

    def get_item_from_disk(self, item):
        return self.ro.get_item(item[u'id'])

    def test_exception_message_contains_id(self):
        obj_id = u'this is unlikely in an error message'
        e = unifiedapi.CannotAddWithId(id=obj_id)
        self.assertIn(obj_id, unicode(e))

    def test_refuses_to_add_item_with_id(self):
        with_id = dict(self.person)
        with_id[u'id'] = u'abc'
        with self.assertRaises(unifiedapi.CannotAddWithId):
            self.wo.add_item(with_id)

    def test_refuses_to_add_item_with_revision(self):
        with_id = dict(self.person)
        with_id[u'revision'] = u'abc'
        with self.assertRaises(unifiedapi.CannotAddWithRevision):
            self.wo.add_item(with_id)

    def test_updates_item(self):
        added = self.wo.add_item(self.person)
        person_v2 = dict(added)
        person_v2[u'name'] = u'Bruce Wayne'
        updated = self.wo.update_item(person_v2)
        self.assertNotEqual(added[u'revision'], updated[u'revision'])
        obj = self.get_item_from_disk(added)
        self.assertEqual(updated, obj)

    def test_refuses_to_update_item_with_wrong_revision(self):
        added = self.wo.add_item(self.person)
        person_v2 = dict(added)
        person_v2[u'name'] = u'Bruce Wayne'
        person_v2[u'revision'] = 'this-is-not-the-latest-revision'

        with self.assertRaises(unifiedapi.WrongRevision):
            self.wo.update_item(person_v2)

        obj = self.get_item_from_disk(added)
        self.assertEqual(added, obj)

    def test_deletes_item(self):
        added = self.wo.add_item(self.person)
        self.wo.delete_item(added[u'id'])
        with self.assertRaises(unifiedapi.ItemDoesNotExist):
            self.ro.get_item(added[u'id'])

    def test_deletes_only_requested_item(self):
        added1 = self.wo.add_item(self.person)
        added2 = self.wo.add_item(self.person)
        self.wo.delete_item(added1[u'id'])
        self.assertEqual(self.ro.get_item_ids(), [added2[u'id']])

    def test_updates_subitem(self):
        added = self.wo.add_item(self.person)
        subitem = {
            u'secret_identity': u'Peter Parker',
        }
        self.wo.update_subitem(
            added[u'id'], added[u'revision'], self.subitem_name, subitem)
        self.ro.get_subitem(added[u'id'], self.subitem_name)
        updated_item = self.ro.get_item(added[u'id'])
        self.assertNotEqual(updated_item[u'revision'], added[u'revision'])

    def test_refuses_to_update_subitem_without_correct_revision(self):
        added = self.wo.add_item(self.person)
        subitem = {
            u'secret_identity': u'Peter Parker',
        }
        with self.assertRaises(unifiedapi.WrongRevision):
            self.wo.update_subitem(
                added[u'id'], 'wrong-revision', self.subitem_name, subitem)

        item = self.ro.get_item(added[u'id'])
        self.assertEqual(item, added)