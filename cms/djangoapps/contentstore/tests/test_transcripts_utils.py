""" Tests for transcripts_utils. """
from contentstore import transcripts_utils
import mock
import unittest
import collections
import copy
import json
from uuid import uuid4

from django.test import TestCase
from xmodule.modulestore.tests.factories import CourseFactory
from django.test.utils import override_settings

from xmodule.contentstore.content import StaticContent
from xmodule.contentstore.django import contentstore
from xmodule.modulestore.tests.djangp_utils import ModuleStoreTestCase
from xmodule.exceptions import NotFoundError


class TestReturnAjaxStatus(unittest.TestCase):
    """Tests for `return_ajax_status` decorator."""
    def setUp(self):
        self.true_view_func = lambda *args, **kwargs: True
        self.true_extra_view_func = lambda *args, **kwargs: (True, {'msg': 'some message'})
        self.false_view_func = lambda *args, **kwargs: False

    def test_success_response(self):
        request = None
        response = transcripts_utils.return_ajax_status(self.true_view_func)(request)
        status = json.loads(response.content).get('success')
        self.assertTrue(status)

    def test_fail_response(self):
        request = None
        response = transcripts_utils.return_ajax_status(self.false_view_func)(request)
        status = json.loads(response.content).get('success')
        self.assertFalse(status)

    def test_extra_response_data(self):
        request = None
        response = transcripts_utils.return_ajax_status(self.true_extra_view_func)(request)
        resp = json.loads(response.content)

        self.assertTrue(resp.get('success'))
        self.assertEqual(resp.get('msg'), 'some message')


class TestGenerateSubs(unittest.TestCase):
    """Tests for `generate_subs` function."""
    def setUp(self):
        self.source_subs = {
            'start': [100, 200, 240, 390, 1000],
            'end': [200, 240, 380, 1000, 1500],
            'text': [
                'subs #1',
                'subs #2',
                'subs #3',
                'subs #4',
                'subs #5'
            ]
        }

    def test_generate_subs_increase_speed(self):
        subs = transcripts_utils.generate_subs(2, 1, self.source_subs)
        self.assertDictEqual(
            subs,
            {
                'start': [200, 400, 480, 780, 2000],
                'end': [400, 480, 760, 2000, 3000],
                'text': ['subs #1', 'subs #2', 'subs #3', 'subs #4', 'subs #5']
            }
        )

    def test_generate_subs_decrease_speed_1(self):
        subs = transcripts_utils.generate_subs(0.5, 1, self.source_subs)
        self.assertDictEqual(
            subs,
            {
                'start': [50, 100, 120, 195, 500],
                'end': [100, 120, 190, 500, 750],
                'text': ['subs #1', 'subs #2', 'subs #3', 'subs #4', 'subs #5']
            }
        )

    def test_generate_subs_decrease_speed_2(self):
        """Test for correct devision during `generate_subs` process."""
        subs = transcripts_utils.generate_subs(1, 2, self.source_subs)
        self.assertDictEqual(
            subs,
            {
                'start': [50, 100, 120, 195, 500],
                'end': [100, 120, 190, 500, 750],
                'text': ['subs #1', 'subs #2', 'subs #3', 'subs #4', 'subs #5']
            }
        )


class TestSaveSubsToStore(ModuleStoreTestCase):
    """Tests for `save_subs_to_store` function."""

    org = 'MITx'
    number = '999'
    display_name = 'Test course'

    def clear_subs_content(self):
        """Remove, if subtitles content exists."""
        try:
            content = contentstore().find(self.content_location)
            contentstore().delete(content.get_id())
        except NotFoundError:
            pass

    def setUp(self):
        self.subs = {
            'start': [100, 200, 240, 390, 1000],
            'end': [200, 240, 380, 1000, 1500],
            'text': [
                'subs #1',
                'subs #2',
                'subs #3',
                'subs #4',
                'subs #5'
            ]
        }

        self.subs_id = str(uuid4())
        filename = 'subs_{0}.srt.sjson'.format(self.subs_id)
        self.course = CourseFactory.create(
            org=self.org, number=self.number, display_name=self.display_name)
        self.content_location = StaticContent.compute_location(
            self.org, self.number, filename)

        self.clear_subs_content()

    def test_save_subs_to_store(self):
        self.assertRaises(
            NotFoundError,
            contentstore().find,
            self.content_location
        )

        result_location = transcripts_utils.save_subs_to_store(
            self.subs,
            self.subs_id,
            self.course)

        self.assertTrue(contentstore().find(self.content_location))
        self.assertEqual(result_location, self.content_location)

    def tearDown(self):
        self.clear_subs_content()


class TestDownloadYoutubeSubs(ModuleStoreTestCase):
    """Tests for `download_youtube_subs` function."""

    org = 'MITx'
    number = '999'
    display_name = 'Test course'

    def clear_subs_content(self, youtube_subs):
        """Remove, if subtitles content exists."""
        for subs_id in youtube_subs.values():
            filename = 'subs_{0}.srt.sjson'.format(subs_id)
            content_location = StaticContent.compute_location(
                self.org, self.number, filename)
            try:
                content = contentstore().find(content_location)
                contentstore().delete(content.get_id())
            except NotFoundError:
                pass

    def setUp(self):
        self.course = CourseFactory.create(
            org=self.org, number=self.number, display_name=self.display_name)

    def test_success_downloading_subs(self):
        good_youtube_subs = {
            0.5: 'JMD_ifUUfsU',
            1.0: 'hI10vDNYz4M',
            2.0: 'AKqURZnYqpk'
        }
        self.clear_subs_content(good_youtube_subs)

        status = transcripts_utils.download_youtube_subs(good_youtube_subs, self.course)
        self.assertTrue(status)

        # Check assets status after importing subtitles.
        for subs_id in good_youtube_subs.values():
            filename = 'subs_{0}.srt.sjson'.format(subs_id)
            content_location = StaticContent.compute_location(
                self.org, self.number, filename)
            self.assertTrue(contentstore().find(content_location))

        self.clear_subs_content(good_youtube_subs)

    def test_fail_downloading_subs(self):
        bad_youtube_subs = {
            0.5: 'BAD_YOUTUBE_ID1',
            1.0: 'BAD_YOUTUBE_ID2',
            2.0: 'BAD_YOUTUBE_ID3'
        }
        self.clear_subs_content(bad_youtube_subs)

        status = transcripts_utils.download_youtube_subs(bad_youtube_subs, self.course)
        self.assertFalse(status)

        # Check assets status after importing subtitles.
        for subs_id in bad_youtube_subs.values():
            filename = 'subs_{0}.srt.sjson'.format(subs_id)
            content_location = StaticContent.compute_location(
                self.org, self.number, filename)
            self.assertRaises(
                NotFoundError, contentstore().find, content_location)

        self.clear_subs_content(bad_youtube_subs)


class TestGenerateSubsFromSource(TestDownloadYoutubeSubs):
    """Tests for `generate_subs_from_source` function."""

    def test_success_generating_subs(self):
        youtube_subs = {
            0.5: 'JMD_ifUUfsU',
            1.0: 'hI10vDNYz4M',
            2.0: 'AKqURZnYqpk'
        }
        srt_filedata = """
1
00:00:10,500 --> 00:00:13,000
Elephant's Dream

2
00:00:15,000 --> 00:00:18,000
At the left we can see...
        """
        self.clear_subs_content(youtube_subs)

        status, __ = transcripts_utils.generate_subs_from_source(
            youtube_subs,
            'srt',
            srt_filedata,
            self.course)
        self.assertTrue(status)

        # Check assets status after importing subtitles.
        for subs_id in youtube_subs.values():
            filename = 'subs_{0}.srt.sjson'.format(subs_id)
            content_location = StaticContent.compute_location(
                self.org, self.number, filename)
            self.assertTrue(contentstore().find(content_location))

        self.clear_subs_content(youtube_subs)

    def test_fail_bad_subs_type(self):
        youtube_subs = {
            0.5: 'JMD_ifUUfsU',
            1.0: 'hI10vDNYz4M',
            2.0: 'AKqURZnYqpk'
        }

        srt_filedata = """
1
00:00:10,500 --> 00:00:13,000
Elephant's Dream

2
00:00:15,000 --> 00:00:18,000
At the left we can see...
        """

        status, __ = transcripts_utils.generate_subs_from_source(
            youtube_subs,
            'BAD_FORMAT',
            srt_filedata,
            self.course)
        self.assertFalse(status)

    def test_fail_bad_subs_filedata(self):
        youtube_subs = {
            0.5: 'JMD_ifUUfsU',
            1.0: 'hI10vDNYz4M',
            2.0: 'AKqURZnYqpk'
        }

        srt_filedata = """BAD_DATA"""

        status, __ = transcripts_utils.generate_subs_from_source(
            youtube_subs,
            'srt',
            srt_filedata,
            self.course)
        self.assertFalse(status)


class TestGenerateSrtFromSjson(TestDownloadYoutubeSubs):
    """Tests for `generate_srt_from_sjson` function."""

    def test_success_generating_subs(self):
        sjson_subs = {
            'start': [100, 200, 240, 390, 54000],
            'end': [200, 240, 380, 1000, 78400],
            'text': [
                'subs #1',
                'subs #2',
                'subs #3',
                'subs #4',
                'subs #5'
            ]
        }
        srt_subs = transcripts_utils.generate_srt_from_sjson(sjson_subs, 1)
        self.assertIsNotNone(srt_subs)
        self.assertIn(
            '00:00:00,100 --> 00:00:00,200\nsubs #1',
            srt_subs)
        self.assertIn(
            '00:00:00,200 --> 00:00:00,240\nsubs #2',
            srt_subs)
        self.assertIn(
            '00:00:00,240 --> 00:00:00,380\nsubs #3',
            srt_subs)
        self.assertIn(
            '00:00:00,390 --> 00:00:01,000\nsubs #4',
            srt_subs)
        self.assertIn(
            '00:00:54,000 --> 00:01:18,400\nsubs #5',
            srt_subs)

    def test_success_generating_subs_speed_up(self):
        sjson_subs = {
            'start': [100, 200, 240, 390, 54000],
            'end': [200, 240, 380, 1000, 78400],
            'text': [
                'subs #1',
                'subs #2',
                'subs #3',
                'subs #4',
                'subs #5'
            ]
        }
        srt_subs = transcripts_utils.generate_srt_from_sjson(sjson_subs, 0.5)
        self.assertIsNotNone(srt_subs)
        self.assertIn(
            '00:00:00,050 --> 00:00:00,100\nsubs #1',
            srt_subs)
        self.assertIn(
            '00:00:00,100 --> 00:00:00,120\nsubs #2',
            srt_subs)
        self.assertIn(
            '00:00:00,120 --> 00:00:00,190\nsubs #3',
            srt_subs)
        self.assertIn(
            '00:00:00,195 --> 00:00:00,500\nsubs #4',
            srt_subs)
        self.assertIn(
            '00:00:27,000 --> 00:00:39,200\nsubs #5',
            srt_subs)

    def test_success_generating_subs_speed_down(self):
        sjson_subs = {
            'start': [100, 200, 240, 390, 54000],
            'end': [200, 240, 380, 1000, 78400],
            'text': [
                'subs #1',
                'subs #2',
                'subs #3',
                'subs #4',
                'subs #5'
            ]
        }
        srt_subs = transcripts_utils.generate_srt_from_sjson(sjson_subs, 2)
        self.assertIsNotNone(srt_subs)
        self.assertIn(
            '00:00:00,200 --> 00:00:00,400\nsubs #1',
            srt_subs)
        self.assertIn(
            '00:00:00,400 --> 00:00:00,480\nsubs #2',
            srt_subs)
        self.assertIn(
            '00:00:00,480 --> 00:00:00,760\nsubs #3',
            srt_subs)
        self.assertIn(
            '00:00:00,780 --> 00:00:02,000\nsubs #4',
            srt_subs)
        self.assertIn(
            '00:01:48,000 --> 00:02:36,800\nsubs #5',
            srt_subs)

    def test_fail_generating_subs(self):
        sjson_subs = {
            'start': [100, 200],
            'end': [100],
            'text': [
                'subs #1',
                'subs #2'
            ]
        }
        srt_subs = transcripts_utils.generate_srt_from_sjson(sjson_subs, 1)
        self.assertIsNone(srt_subs)