import unittest

from src.info import Info


class UbuntuTorrentTests(unittest.TestCase):
    def setUp(self):
        self.t = Info('./data/ubuntu.iso.torrent')

    def test_instantiate(self):
        self.assertIsNotNone(self.t)

    def test_is_single_file(self):
        self.assertFalse(self.t.is_multi_file)

    def test_announce(self):
        self.assertEqual(
            'http://torrent.ubuntu.com:6969/announce', self.t.announce)

    def test_piece_length(self):
        self.assertEqual(
            524288, self.t.piece_length)

    # def test_file(self):
        # self.assertEqual(1, len(self.t.files))
        # self.assertEqual(
        #     'ubuntu-16.04-server-amd64.iso', self.t.files[0].name)
        # self.assertEqual(1485881344, self.t.files[0].length)

    def test_hash_value(self):
        # hexdigest of the SHA1 '4344503b7e797ebf31582327a5baae35b11bda01',
        self.assertEqual(
            b'\xa4\x10J\x9d/V\x15`\x1cB\x9f\xe8\xba\xb8\x17|G\xc0\\\x84',
            self.t.hash20)

    def test_total_size(self):
        self.assertEqual(851443712, self.t.length)

    def test_pieces(self):
        self.assertEqual(1624, len(self.t.pieces))
