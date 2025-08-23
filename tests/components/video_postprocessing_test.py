import unittest
from unittest.mock import patch, MagicMock, call

from components.video_processing.video_preprocessing import VideoPreprocessing
from utils.data_structures import MediaClip, DataTypeEnum, LoadedVideo


class TestVideoPreprocessing(unittest.TestCase):
    def setUp(self):
        self.vp = VideoPreprocessing()
        self.temp_file = 'temp/test.mp4'
        self.media_dir = '/media'
        self.file_path = 'video.mp4'

    @patch('os.remove')
    def test_cleanup_temp_files(self, mock_remove):
        # Add temp files
        self.vp.temp_cfr_files = ['file1.mp4', 'file2.mp4']

        self.vp.cleanup_temp_files()
        mock_remove.assert_has_calls([call('file1.mp4'), call('file2.mp4')])

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    def test_convert_to_cfr_new_file(self, mock_makedirs, mock_exists, mock_run):
        input_path = 'video.mp4'
        output = self.vp.convert_to_cfr(input_path, target_fps=24)

        # Check subprocess run called with ffmpeg
        self.assertIn('_cfr_24fps.mp4', output)
        mock_run.assert_called_once()

        # Check caches updated
        self.assertIn(input_path, self.vp.cfr_cache)
        self.assertIn(output, self.vp.temp_cfr_files)

    @patch('os.path.exists', return_value=True)
    def test_convert_to_cfr_cached_file(self, mock_exists):
        input_path = 'video.mp4'
        # Pre-fill cache
        cached_path = 'temp/video_cfr_30fps.mp4'
        self.vp.cfr_cache[input_path] = cached_path

        result = self.vp.convert_to_cfr(input_path)
        self.assertEqual(result, cached_path)

    @patch('subprocess.check_output')
    def test_is_variable_framerate_var(self, mock_check):
        # r_frame_rate != avg_frame_rate
        mock_check.return_value = b'30000/1001\n29.97/1\n'
        is_var, avg = self.vp.is_variable_framerate('file.mp4')
        self.assertTrue(is_var)
        self.assertEqual(avg, 29)

    @patch('subprocess.check_output')
    def test_is_variable_framerate_non_var(self, mock_check):
        mock_check.return_value = b'30/1\n30/1\n'
        is_var, avg = self.vp.is_variable_framerate('file.mp4')
        self.assertFalse(is_var)
        self.assertEqual(avg, 30)

    @patch('components.video_processing.video_preprocessing.VideoFileClip')
    @patch('components.video_processing.video_preprocessing.format_photo_to_vertical')
    def test_process_entry_video(self, mock_format, mock_videoclip):
        # Setup
        clip_mock = MagicMock()
        clip_mock.duration = 10
        clip_mock.subclip.return_value = clip_mock
        mock_videoclip.return_value = clip_mock

        entry = MediaClip(type=DataTypeEnum.VIDEO.value, start=0, end=5, video_resampling=True, transition=None)

        # Patch is_variable_framerate to avoid actual ffprobe
        with patch.object(self.vp, 'is_variable_framerate', return_value=(False, 30)):
            loaded = self.vp.process_entry(self.file_path, entry, self.media_dir)

        mock_videoclip.assert_called_once()
        self.assertIsInstance(loaded, LoadedVideo)

    @patch('components.video_processing.video_preprocessing.ImageClip')
    @patch('components.video_processing.video_preprocessing.format_photo_to_vertical')
    def test_process_entry_photo(self, mock_format, mock_imageclip):
        img_clip_mock = MagicMock()
        img_clip_mock.set_duration.return_value = img_clip_mock
        mock_imageclip.return_value = img_clip_mock
        mock_format.return_value = 'formatted.jpg'

        entry = MediaClip(type=DataTypeEnum.PHOTO.value, start=0, end=5, video_resampling=False, transition=None)

        loaded = self.vp.process_entry(self.file_path, entry, self.media_dir)

        mock_format.assert_called_once()
        mock_imageclip.assert_called_once_with('formatted.jpg')
        self.assertIsInstance(loaded, LoadedVideo)

    def test_process_entry_invalid_type(self):
        entry = MediaClip(type='unsupported', start=0, end=1, video_resampling=False, transition=None)

        with self.assertRaises(ValueError):
            self.vp.process_entry(self.file_path, entry, self.media_dir)
