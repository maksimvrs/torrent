import asyncio
import logging
from asyncio import Queue
from concurrent.futures import CancelledError

from src.peer_protocol import *
from src.peer_streem_iterator import PeerStreamIterator

# The default request size for blocks of pieces is 2^14 bytes.
#
# NOTE: The official specification states that 2^15 is the default request
#       size - but in reality all implementations use 2^14. See the
#       unofficial specification for more details on this matter.
#
#       https://wiki.theory.org/BitTorrentSpecification
#

REQUEST_SIZE = 2 ** 14


class ProtocolError(BaseException):
    pass


class PeerState:
    Unchoke = 0
    Choked = 1
    Interested = 2
    PendingRequest = 3
    Stopped = 4


class PeerConnection:
    """
    A peer connection used to download and upload pieces.

    The peer connection will consume one available peer from the given queue.
    Based on the peer details the PeerConnection will try to open a connection
    and perform a BitTorrent handshake.

    After a successful handshake, the PeerConnection will be in a *choked*
    state, not allowed to request any data from the remote peer. After sending
    an interested message the PeerConnection will be waiting to get *unchoked*.

    Once the remote peer unchoked us, we can start requesting pieces.
    The PeerConnection will continue to request pieces for as long as there are
    pieces left to request, or until the remote peer disconnects.

    If the connection with a remote peer drops, the PeerConnection will consume
    the next available peer from off the queue and try to connect to that one
    instead.
    """

    def __init__(self, queue: Queue, info_hash,
                 peer_id, piece_manager, on_block_cb=None):
        """
        Constructs a PeerConnection and add it to the asyncio event-loop.

        Use `stop` to abort this connection and any subsequent connection
        attempts

        :param queue: The async Queue containing available peers
        :param info_hash: The SHA1 hash for the meta-data's info
        :param peer_id: Our peer ID used to to identify ourselves
        :param piece_manager: The manager responsible to determine which pieces
                              to request
        :param on_block_cb: The callback function to call when a block is
                            received from the remote peer
        """
        self.my_state = []
        self.peer_state = []
        self.queue = queue
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.remote_id = None
        self.writer = None
        self.reader = None
        self.piece_manager = piece_manager
        self.on_block_cb = on_block_cb
        self.future = asyncio.ensure_future(self._start())  # Start this worker

    async def _start(self):
        while PeerState.Stopped not in self.my_state:
            peer = await self.queue.get()
            self.my_state = []
            self.peer_state = []
            ip, port = peer
            logging.info('Got assigned peer with: {ip}'.format(ip=ip))
            try:
                # TODO For some reason it does not seem to work to open a new
                # connection if the first one drops (i.e. second loop).
                self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(ip, port), 30)
                logging.info('Connection open to peer: {ip}'.format(ip=ip))

                # It's our responsibility to initiate the handshake.
                buffer = await self._handshake()

                # TODO Add support for sending data
                # Sending BitField is optional and not needed when client does
                # not have any pieces. Thus we do not send any bitfield message

                # The default state for a connection is that peer is not
                # interested and we are choked
                self.peer_state.append(PeerState.Choked)

                # Let the peer know we're interested in downloading pieces
                await self._send_interested()
                self.my_state.append(PeerState.Interested)

                # Start reading responses as a stream of messages for as
                # long as the connection is open and data is transmitted
                async for message in PeerStreamIterator(self.reader, buffer):
                    if PeerState.Stopped in self.my_state:
                        break
                    if message is None:
                        if PeerState.PendingRequest in self.my_state:
                            self.my_state.remove(PeerState.PendingRequest)
                    elif type(message) is BitField:
                        self.piece_manager.add_peer(self.remote_id,
                                                    message.bitfield)
                    elif type(message) is Interested:
                        self.peer_state.append(PeerState.Interested)
                    elif type(message) is NotInterested:
                        if PeerState.Interested in self.peer_state:
                            self.peer_state.remove(PeerState.Interested)
                    elif type(message) is Choke:
                        self.peer_state.append(PeerState.Choked)
                    elif type(message) is Unchoke:
                        logging.info(PeerState.Unchoke)
                        if PeerState.PendingRequest in self.my_state:
                            self.my_state.remove(PeerState.PendingRequest)
                        if PeerState.Choked in self.peer_state:
                            self.peer_state.remove(PeerState.Choked)
                    elif type(message) is Have:
                        if PeerState.PendingRequest in self.my_state:
                            self.my_state.remove(PeerState.PendingRequest)
                        self.piece_manager.update_peer(self.remote_id,
                                                       message.index)
                    elif type(message) is KeepAlive:
                        if PeerState.PendingRequest in self.my_state:
                            self.my_state.remove(PeerState.PendingRequest)
                        pass
                    elif type(message) is Piece:
                        self.my_state.remove(PeerState.PendingRequest)
                        self.on_block_cb(
                            peer_id=self.remote_id,
                            piece_index=message.index,
                            block_offset=message.begin,
                            data=message.block)
                    elif type(message) is Request:
                        for piece in self.piece_manager.have_pieces:
                            if piece[message.index].is_complete():
                                data = self.piece_manager.file_manager.read(message.index, message.begin, message.length)
                                self.writer.write(Piece(message.index, message.begin, data).encode())
                                await self.writer.drain()
                                logging.info("Send data")
                    elif type(message) is Cancel:
                        pass

                    logging.info(ip + ": " + str(self.peer_state) + str(self.my_state))

                    # Send block request to remote peer if we're interested
                    if PeerState.Choked not in self.peer_state:
                        if PeerState.Interested in self.my_state:
                            if PeerState.PendingRequest not in self.my_state:
                                self.my_state.append(PeerState.PendingRequest)
                                await self._request_piece()

            except ProtocolError as e:
                logging.exception('Protocol error: ' + str(e))
            except (ConnectionRefusedError, TimeoutError):
                logging.warning('Unable to connect to peer')
            except (ConnectionResetError, CancelledError):
                logging.warning('Connection closed')
            except StopAsyncIteration as e:
                logging.exception(e)
                await self.cancel()
            except Exception as e:
                logging.exception('Undefind error: ' + str(e) + str(message))
                await self.cancel()
                continue
        await self.cancel()
        self.stop()

    async def cancel(self, index, begin):
        """
        Sends the cancel message to the remote peer and closes the connection.
        """
        logging.info('Closing peer {id}'.format(id=self.remote_id))

        self.writer.write(Cancel(index, begin))
        await self.writer.drain()

    def stop(self):
        """
        Stop this connection from the current peer (if a connection exist) and
        from connecting to any new peer.
        """
        # Set state to stopped and cancel our future to break out of the loop.
        # The rest of the cleanup will eventually be managed by loop calling
        # `cancel`.

        self.my_state.append(PeerState.Stopped)
        if self.writer:
            self.writer.close()
        # if self.queue:
        #     self.queue.task_done()
        if not self.future.done():
            self.future.cancel()

    async def _request_piece(self):
        block = self.piece_manager.next_request(self.remote_id)
        if block:
            message = Request(block.piece, block.offset, block.length).encode()

            logging.debug('Requesting block {block} for piece {piece} '
                          'of {length} bytes from peer {peer}'.format(
                piece=block.piece,
                block=block.offset,
                length=block.length,
                peer=self.remote_id))

            self.writer.write(message)
            await self.writer.drain()

    async def _handshake(self):
        """
        Send the initial handshake to the remote peer and wait for the peer
        to respond with its handshake.
        """
        self.writer.write(Handshake(self.info_hash, self.peer_id).encode())
        await self.writer.drain()

        buf = b''
        while len(buf) < Handshake.length:
            buf = await asyncio.wait_for(self.reader.read(PeerStreamIterator.CHUNK_SIZE), 15)

        response = Handshake.decode(buf[:Handshake.length])
        if not response:
            raise ProtocolError('Unable receive and parse a handshake')
        if not response.info_hash == self.info_hash:
            # print(response.info_hash, self.info_hash)
            raise ProtocolError('Handshake with invalid info_hash')

        # TODO: According to spec we should validate that the peer_id received
        # from the peer match the peer_id received from the tracker.
        self.remote_id = response.peer_id
        logging.info('Handshake with peer was successful')

        # We need to return the remaining buffer data, since we might have
        # read more bytes then the size of the handshake message and we need
        # those bytes to parse the next message.
        return buf[Handshake.length:]

    async def _send_interested(self):
        message = Interested()
        logging.debug('Sending message: {type}'.format(type=message))
        self.writer.write(message.encode())
        await self.writer.drain()
