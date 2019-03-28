import os


class FileManager:
    def __init__(self, info, files, work_path):
        """
        Args:
            info: Torrent info dictionary.
            files: List of indices required for downloading files.
                   File order as in info.
            work_path: Folder for downloading files.
        """
        self.info = info
        self.files = files
        self.work_path = work_path
        if self.info.is_multi_file:
            self.fd = []
        else:
            self.fd = None

    def need_piece(self, piece):
        if not self.info.is_multi_file:
            return True
        else:
            offset = 0
            for i, file in enumerate(self.info.files):
                if offset < self.info.piece_length * piece.index:
                    if i in self.files:
                        return True
                    offset += file['length']
        return False

    def open(self):
        if self.info.is_multi_file:
            for i in self.files:
                directory = ""
                for subdir in self.info.files[i]['path'][:-1]:
                    directory += subdir
                    if not os.path.exists(self.work_path + directory):
                        os.makedirs(self.work_path + directory)
                self.fd.append(
                    os.open(self.work_path
                            + directory
                            + self.info.files[i]['path'][-1],
                            os.O_RDWR | os.O_CREAT))
        else:
            self.fd = os.open(self.work_path + self.info.name,
                              os.O_RDWR | os.O_CREAT)

    def write(self, piece):
        if self.info.is_multi_file:
            begin = []
            offset = 0
            for i, file in enumerate(self.info.files):
                if offset < self.info.piece_length * piece.index:
                    begin.append(
                        (i, self.info.piece_length * piece.index - offset))
                    if self.info.piece_length * \
                            (piece.index + 1) < offset + file['length']:
                        break
                else:
                    offset += file['length']
            piece_offset = 0
            for file in begin:
                os.lseek(self.fd[file[0]], file[1], os.SEEK_SET)
                os.write(self.fd[file[0]],
                         piece.data[piece_offset:min(
                             piece_offset + self.info.files[file[0]],
                             len(piece.data) - piece_offset)])
                piece_offset = min(piece_offset + self.info.files[file[0]],
                                   len(piece.data) - piece_offset)
        else:
            pos = piece.index * self.info.piece_length
            os.lseek(self.fd, pos, os.SEEK_SET)
            os.write(self.fd, piece.data)

    def read(self, index, offset, length):
        if self.info.is_multi_file:
            data = b''
            files_offset = 0
            for i, file in enumerate(self.info.files):
                if files_offset < self.info.piece_length * index + offset:
                    os.lseek(self.fd[i], index
                             * self.info.piece_length + offset, os.SEEK_SET)
                    data += os.read(self.fd[i], length)
                    if self.info.piece_length * index + offset + \
                            length < files_offset + file['length']:
                        break
                else:
                    offset += file['length']
            return data
        else:
            os.lseek(self.fd, index * self.info.piece_length
                     + offset, os.SEEK_SET)
            return os.read(self.fd, length)

    def close(self):
        if self.info.is_multi_file:
            for file in self.fd:
                os.close(file)
        else:
            os.close(self.fd)
