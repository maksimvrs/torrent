import asyncio
import logging
import math
import time
import hashlib
from asyncio import Queue

from src.tracker import Tracker
from src.peer import PeerConnection, REQUEST_SIZE
from src.uploader import Uploader
from src.file_manager import FileManager


class TorrentClient:
    """
    The torrent client is the local peer that holds peer-to-peer
    connections to download and upload pieces for a given torrent.

    Once started, the client makes periodic announce calls to the tracker
    registered in the torrent meta-data. These calls results in a list of
    peers that should be tried in order to exchange pieces.

    Each received peer is kept in a queue that a pool of PeerConnection
    objects consume. There is a fix number of PeerConnections that can have
    a connection open to a peer. Since we are not creating expensive threads
    (or worse yet processes) we can create them all at once and they will
    be waiting until there is a peer to consume in the queue.
    """

    MAX_PEER_CONNECTIONS = 35
    MAX_PEER_UPLOAD_CONNECTIONS = 15
    SPEED_CALCULATE_INTERVAL = 1

    def __init__(self, info, files, work_path):
        self.tracker = Tracker(info)
        self.info = info

        self.files = files
        self.work_path = work_path

        self.prev_speed_check_time = None
        self.downloaded = []
        self.speed = 0
        # self.dht = btdht.DHT()

        # The list of potential peers is the work queue, consumed by the
        # PeerConnections
        self.available_peers = Queue()
        # The list of peers is the list of workers that *might* be connected
        # to a peer. Else they are waiting to consume new remote peers from
        # the `available_peers` queue. These are our workers!
        self.peers = []
        # The piece manager implements the strategy on which pieces to
        # request, as well as the logic to persist received pieces to disk.

        self.uploader_queue = Queue()
        self.uploaders = []

        self.listener = None

        self.piece_manager = PieceManager(info, self.files, self.work_path)
        self.abort = False

    async def start(self):
        """
        Start downloading the torrent held by this client.

        This results in connecting to the tracker to retrieve the list of
        peers to communicate with. Once the torrent is fully downloaded or
        if the download is aborted this method will complete.
        """
        self.listener = asyncio.ensure_future(self.listen())

        self.peers = [PeerConnection(self.available_peers,
                                     self.tracker.info.hash20,
                                     self.info.peer_id,
                                     self.piece_manager,
                                     self._on_block_retrieved)
                      for _ in range(self.MAX_PEER_CONNECTIONS)]
        self.piece_manager.start_time = time.time()

        self.uploaders = [Uploader(
            self.uploader_queue,
            self.piece_manager
        )] * self.MAX_PEER_UPLOAD_CONNECTIONS

        first = True
        interval = 15

        self.prev_speed_check_time = time.time()

        while True:
            try:
                response = await self.tracker.connect(
                    first=first,
                    uploaded=self.piece_manager.bytes_uploaded,
                    downloaded=self.piece_manager.bytes_downloaded
                )
                # logging.info("Tracker response: {resp}".format(
                #   resp=(response if response is not None else 'None')))

                if response:
                    first = False
                    interval = response.interval
                    self._empty_queue()
                    for peer in response.peers:
                        await self.available_peers.put(peer)

            except Exception as e:
                raise e

            await asyncio.sleep(interval)

            # dht_previous = None
            # dht_interval = 5 * 60
            #
            # current = time.time()
            #
            # if (dht_previous is None) or \
            #       (dht_previous + dht_interval) < current:
            #     try:
            #         response = await self.tracker.connect_dht()
            #         print("DHT: ", response)
            #         if response:
            #             dht_previous = current
            #             # for peer in response.peers:
            #             #     if peer not in self.available_peers:
            #             #         self.available_peers.put_nowait(peer)
            #     except Exception as e:
            #         print("DHT ERROR: ", e)
            #         pass

            # await self.stop()

    def _empty_queue(self):
        while not self.available_peers.empty():
            self.available_peers.get_nowait()

    async def stop(self):
        """
        Stop the download or seeding process.
        """
        self.abort = True
        for peer in self.peers:
            peer.stop()
        self.piece_manager.file_manager.close()
        await self.tracker.close()

    def _on_block_retrieved(self, peer_id, piece_index, block_offset, data):
        """
        Callback function called by the `PeerConnection` when a block is
        retrieved from a peer.

        :param peer_id: The id of the peer the block was retrieved from
        :param piece_index: The piece index this block is a part of
        :param block_offset: The block offset within its piece
        :param data: The binary data retrieved
        """
        self.downloaded.append((len(data), time.time()))
        if time.time() - self.prev_speed_check_time \
                >= self.SPEED_CALCULATE_INTERVAL:
            while len(self.downloaded) >= 2 and self.downloaded[-1][1]\
                  - self.downloaded[0][1] > self.SPEED_CALCULATE_INTERVAL * 5:
                del self.downloaded[0]
            size = sum([i[0] for i in self.downloaded])
            time_interval = self.downloaded[-1][1] - self.downloaded[0][1]
            self.speed = size / time_interval
            self.prev_speed_check_time = time.time()

        self.piece_manager.block_received(
            peer_id=peer_id, piece_index=piece_index,
            block_offset=block_offset, data=data)

    async def new_connection_handle(self, reader, writer):
        self.uploader_queue.put_nowait((reader, writer))

    async def listen(self):
        server = await asyncio.start_server(self.new_connection_handle,
                                            '0.0.0.0', 6889)
        addr = server.sockets[0].getsockname()
        async with server:
            await server.serve_forever()


class Block:
    """
    The block is a partial piece, this is what is requested and transferred
    between peers.

    The recommended block size is 2^14 (16KB).
    """
    Missing = 0
    Pending = 1
    Retrieved = 2

    def __init__(self, piece: int, offset: int, length: int):
        self.piece = piece
        self.offset = offset
        self.length = length
        self.status = Block.Missing
        self.data = None
        self.start_time = None


class Piece:
    """
    The piece is a part of of the torrents content. Each piece except the final
    piece for a torrent has the same length (the final piece might be shorter).

    A piece is what is defined in the torrent meta-data. However, when sharing
    data between peers a smaller unit is used - this smaller piece is refereed
    to as `Block` by the unofficial specification (the official specification
    uses piece for this one as well, which is slightly confusing).
    """

    def __init__(self, index: int, blocks: [], hash_value):
        self.index = index
        self.blocks = blocks
        self.hash = hash_value

    def reset(self):
        """
        Reset all blocks to Missing regardless of current state.
        """
        for block in self.blocks:
            block.status = Block.Missing

    def next_request(self) -> Block:
        """
        Get the next Block to be requested
        """
        missing = [b for b in self.blocks if b.status is Block.Missing]
        if missing:
            missing[0].status = Block.Pending
            return missing[0]
        return None

    def block_received(self, offset: int, data: bytes):
        """
        Update block information that the given block is now received

        :param offset: The block offset (within the piece)
        :param data: The block data
        """
        matches = [b for b in self.blocks if b.offset == offset]
        block = matches[0] if matches else None
        if block:
            block.status = Block.Retrieved
            block.data = data
        else:
            logging.warning('Trying to complete a non-existing block {offset}'
                            .format(offset=offset))

    def is_complete(self) -> bool:
        """
        Checks if all blocks for this piece is retrieved (regardless of SHA1)

        :return: True or False
        """
        blocks = [b for b in self.blocks if b.status is not Block.Retrieved]
        return len(blocks) is 0

    def is_hash_matching(self) -> bool:
        """
        Check if a SHA1 hash for all the received blocks match the piece hash
        from the torrent meta-info.

        :return: True or False
        """
        return self.hash == hashlib.sha1(self.data).digest()

    @property
    def data(self):
        """
        Return the data for this piece (by concatenating all blocks in order)

        NOTE: This method does not control that all blocks are valid or even
        existing!
        """
        retrieved = sorted(self.blocks, key=lambda b: b.offset)
        blocks_data = [b.data for b in retrieved]
        return b''.join(blocks_data)


class PieceManager:
    """
    The PieceManager is responsible for keeping track of all the available
    pieces for the connected peers as well as the pieces we have available for
    other peers.

    The strategy on which piece to request is made as simple as possible in
    this implementation.
    """

    def __init__(self, info, files, work_path):
        self.info = info
        self.files = files
        self.work_path = work_path
        self.file_manager = FileManager(self.info, self.files, self.work_path)
        self.file_manager.open()
        self.start_time = None
        self.peers = {}
        self.pending_blocks = []
        self.missing_pieces = self._init_pieces()
        self.ongoing_pieces = []
        self.have_pieces = []
        self.max_pending_time = 30 * 1000  # 30 second
        self.total_pieces = len(info.pieces)

        # self.have_pieces = self.missing_pieces[0:int(
        #    len(self.missing_pieces)*0.9)]
        # del self.missing_pieces[0:int(len(self.missing_pieces)*0.9)]

    def _init_pieces(self) -> [Piece]:
        """
        Pre-construct the list of pieces and blocks based on the number of
        pieces and request size for this torrent.
        """
        pieces = []
        total_pieces = len(self.info.pieces)
        blocks_number = math.ceil(self.info.piece_length / REQUEST_SIZE)

        for index, hash_value in enumerate(self.info.pieces):
            # The number of blocks for each piece can be calculated using the
            # request size as divisor for the piece length.
            # The final piece however, will most likely have fewer blocks
            # than 'regular' pieces, and that final block might be smaller
            # then the other blocks.
            if index < (total_pieces - 1):
                blocks = [Block(index, offset * REQUEST_SIZE, REQUEST_SIZE)
                          for offset in range(blocks_number)]
            else:
                last_length = self.info.length % self.info.piece_length
                last_blocks_number = math.ceil(last_length / REQUEST_SIZE)
                blocks = [Block(index, offset * REQUEST_SIZE, REQUEST_SIZE)
                          for offset in range(last_blocks_number)]

                if last_length % REQUEST_SIZE > 0:
                    # Last block of the last piece might be smaller than
                    # the ordinary request size.
                    last_block = blocks[-1]
                    last_block.length = last_length % REQUEST_SIZE
                    blocks[-1] = last_block
            piece = Piece(index, blocks, hash_value)
            if self.file_manager.need_piece(piece):
                pieces.append(piece)
        return pieces

    @property
    def is_complete(self):
        """
        Checks whether or not the all pieces are downloaded for this torrent.

        :return: True if all pieces are fully downloaded else False
        """
        return len(self.have_pieces) == self.total_pieces

    def bytes_downloaded_changed(self):
        pass

    @property
    def bytes_downloaded(self) -> int:
        """
        Get the number of bytes downloaded.

        This method Only counts full, verified, pieces, not single blocks.
        """
        return len(self.have_pieces) * self.info.piece_length - \
            ((self.info.length % self.info.piece_length)
             if self.is_complete else 0)

    @property
    def bytes_uploaded(self) -> int:
        return 0

    @property
    def speed(self):
        return self.bytes_downloaded / (time.time() - self.start_time)

    def add_peer(self, peer_id, bitfield):
        """
        Adds a peer and the bitfield representing the pieces the peer has.
        """
        self.peers[peer_id] = bitfield

    def update_peer(self, peer_id, index: int):
        """
        Updates the information about which pieces a peer has (reflects a Have
        message).
        """
        if peer_id in self.peers:
            self.peers[peer_id][index] = 1

    def remove_peer(self, peer_id):
        """
        Tries to remove a previously added peer (e.g. used if a peer connection
        is dropped)
        """
        if peer_id in self.peers:
            del self.peers[peer_id]

    def next_request(self, peer_id) -> Block:
        """
        Get the next Block that should be requested from the given peer.

        If there are no more blocks left to retrieve or if this peer does not
        have any of the missing pieces None is returned
        """
        # The algorithm implemented for which piece to retrieve is a simple
        # one. This should preferably be replaced with an implementation of
        # "rarest-piece-first" algorithm instead.
        #
        # The algorithm tries to download the pieces in sequence and will try
        # to finish started pieces before starting with new pieces.
        #
        # 1. Check any pending blocks to see if any request should be reissued
        #    due to timeout
        # 2. Check the ongoing pieces to get the next block to request
        # 3. Check if this peer have any of the missing pieces not yet started
        if peer_id not in self.peers:
            logging.warning("Peer not in piece manager")
            # return None
            if len(self.missing_pieces) != 0:
                piece = self.missing_pieces.pop(0)
                return piece.next_request()
            return None

        if len(self.missing_pieces) < TorrentClient.MAX_PEER_CONNECTIONS:
            block = self._next_missing(peer_id)
            if not block:
                block = self._expired_requests(peer_id)
                if not block:
                    block = self._next_ongoing(peer_id)
            return block

        block = self._expired_requests(peer_id)
        if not block:
            block = self._next_ongoing(peer_id)
            if not block:
                block = self._next_missing(peer_id)
        return block

    def block_received(self, peer_id, piece_index, block_offset, data):
        """
        This method must be called when a block has successfully been retrieved
        by a peer.

        Once a full piece have been retrieved, a SHA1 hash control is made. If
        the check fails all the pieces blocks are put back in missing state to
        be fetched again. If the hash succeeds the partial piece is written to
        disk and the piece is indicated as Have.
        """
        logging.debug('Received block {block_offset} for piece {piece_index} '
                      'from peer {peer_id}: '.format(block_offset=block_offset,
                                                     piece_index=piece_index,
                                                     peer_id=peer_id))

        self.bytes_downloaded_changed()
        # Remove from pending requests
        for index, request in enumerate(self.pending_blocks):
            if request.piece == piece_index and \
                    request.offset == block_offset:
                del self.pending_blocks[index]
                break

        pieces = [p for p in self.ongoing_pieces if p.index == piece_index]
        piece = pieces[0] if pieces else None
        if piece:
            piece.block_received(block_offset, data)
            if piece.is_complete():
                if piece.is_hash_matching():
                    self.file_manager.write(piece)
                    self.ongoing_pieces.remove(piece)
                    self.have_pieces.append(piece)
                    complete = (self.total_pieces
                                - len(self.missing_pieces)
                                - len(self.ongoing_pieces))
                    logging.info(
                        '{complete} / {total} pieces downloaded {per:.3f} %'
                        .format(complete=complete,
                                total=self.total_pieces,
                                per=(complete / self.total_pieces) * 100))
                else:
                    logging.info('Discarding corrupt piece {index}'
                                 .format(index=piece.index))
                    piece.reset()
        else:
            logging.warning('Trying to update piece that is not ongoing!')

    def _expired_requests(self, peer_id) -> Block:
        """
        Go through previously requested blocks, if any one have been in the
        requested state for longer than `MAX_PENDING_TIME` return the block to
        be re-requested.

        If no pending blocks exist, None is returned
        """
        current = int(round(time.time() * 1000))
        for request in self.pending_blocks:
            # Check Bitfield
            if self.peers[peer_id][request.piece]:
                if request.start_time + self.max_pending_time < current:
                    logging.info('Re-requesting block {block} for '
                                 'piece {piece}'.format(
                                     block=request.offset,
                                     piece=request.piece))
                    # Reset expiration timer
                    request.start_time = current
                    return request
        return None

    def _next_endgame(self, perr_id) -> Block:
        pass

    def _next_ongoing(self, peer_id) -> Block:
        """
        Go through the ongoing pieces and return the next block to be
        requested or None if no block is left to be requested.
        """
        for piece in self.ongoing_pieces:
            # Check Bitfield
            if self.peers[peer_id][piece.index]:
                # Is there any blocks left to request in this piece?
                block = piece.next_request()
                if block:
                    block.start_time = int(round(time.time() * 1000))
                    self.pending_blocks.append(block)
                    return block
        return None

    def _next_missing(self, peer_id) -> Block:
        """
        Go through the missing pieces and return the next block to request
        or None if no block is left to be requested.

        This will change the state of the piece from missing to ongoing - thus
        the next call to this function will not continue with the blocks for
        that piece, rather get the next missing piece.
        """

        if len(self.ongoing_pieces) > 20:
            pieces = [piece.blocks for piece in self.ongoing_pieces]
            blocks = []
            for block in pieces:
                blocks.extend(block)
            for block in blocks:
                if block.status == block.Pending:
                    return block

        for index, piece in enumerate(self.missing_pieces):
            # Check Bitfield
            if self.peers[peer_id][piece.index]:
                # Move this piece from missing to ongoing
                piece = self.missing_pieces.pop(index)
                self.ongoing_pieces.append(piece)
                # The missing pieces does not have any previously requested
                # blocks (then it is ongoing).
                return piece.next_request()
        return None
