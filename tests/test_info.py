import unittest

from src.info import Info


class UbuntuTorrentTests(unittest.TestCase):
    def setUp(self):
        self.t = Info('./ubuntu.iso.torrent')

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
            b'\xc7\xf30|\x8f\x11FM=^\xec\xde^\xc6\x97"\xd5qA\xbe',
            self.t.hash20)

    def test_total_size(self):
        self.assertEqual(912261120, self.t.length)

    def test_pieces(self):
        self.assertEqual(34800, len(self.t.pieces))
