import asyncio
import logging
from concurrent.futures import CancelledError

from src.peer_streem_iterator import PeerStreamIterator
from src.peer import PeerState
from src.peer_protocol import *


class ProtocolError(BaseException):
    pass


class Uploader:
    def __init__(self, queue, piece_manager):
        self.queue = queue
        self.piece_manager = piece_manager
        self.reader = None
        self.writer = None
        self.remote_id = None
        self.my_state = []
        self.peer_state = []

    async def start(self):
        while True:
            self.reader, self.writer = await self.queue.get()
            try:
                # It's our responsibility to initiate the handshake.
                buffer = await self._handshake()

                # TODO Add support for sending data
                # Sending BitField is optional and not needed when client does
                # not have any pieces. Thus we do not send any bitfield message

                # The default state for a connection is that peer is not
                # interested and we are choked
                self.peer_state.append(PeerState.Choked)

                # Start reading responses as a stream of messages for as
                # long as the connection is open and data is transmitted
                async for message in PeerStreamIterator(self.reader, buffer):
                    if PeerState.Stopped in self.my_state:
                        break
                    if message is None:
                        if PeerState.PendingRequest in self.my_state:
                            self.my_state.remove(PeerState.PendingRequest)
                    elif isinstance(message) is BitField:
                        self.piece_manager.add_peer(self.remote_id,
                                                    message.bitfield)
                    elif isinstance(message) is Interested:
                        self.peer_state.append(PeerState.Interested)
                        self.writer.write(Unchoke().encode())
                        await self.writer.drain()
                        if PeerState.Choked in self.my_state:
                            self.my_state.remove(PeerState.Choked)
                    elif isinstance(message) is NotInterested:
                        if PeerState.Interested in self.peer_state:
                            self.peer_state.remove(PeerState.Interested)
                    elif isinstance(message) is Choke:
                        self.peer_state.append(PeerState.Choked)
                    elif isinstance(message) is Unchoke:
                        logging.info(PeerState.Unchoke)
                        if PeerState.PendingRequest in self.my_state:
                            self.my_state.remove(PeerState.PendingRequest)
                        if PeerState.Choked in self.peer_state:
                            self.peer_state.remove(PeerState.Choked)
                    elif isinstance(message) is Have:
                        if PeerState.PendingRequest in self.my_state:
                            self.my_state.remove(PeerState.PendingRequest)
                        self.piece_manager.update_peer(self.remote_id,
                                                       message.index)
                    elif isinstance(message) is KeepAlive:
                        if PeerState.PendingRequest in self.my_state:
                            self.my_state.remove(PeerState.PendingRequest)
                        pass
                    elif isinstance(message) is Piece:
                        self.my_state.remove(PeerState.PendingRequest)
                        self.on_block_cb(
                            peer_id=self.remote_id,
                            piece_index=message.index,
                            block_offset=message.begin,
                            data=message.block)
                    elif isinstance(message) is Request:
                        for piece in self.piece_manager.have_pieces:
                            if piece[message.index].is_complete():
                                data = self.piece_manager.file_manager.read(
                                    message.index, message.begin,
                                    message.length)
                                self.writer.write(
                                    Piece(message.index,
                                          message.begin,
                                          data).encode())
                                await self.writer.drain()
                                logging.info("Send data")
                    elif isinstance(message) is Cancel:
                        pass

            except ProtocolError as error:
                logging.exception('Protocol error: ' + str(error))
            except (ConnectionRefusedError, TimeoutError):
                logging.warning('Unable to connect to peer')
            except (ConnectionResetError, CancelledError):
                logging.warning('Connection closed')
            except StopAsyncIteration as error:
                logging.exception(error)
                await self.close()
            except Exception as error:
                logging.exception('Undefind error: ' +
                                  str(error) + str(message))
                await self.close()

    async def _handshake(self):
        buf = b''
        while len(buf) < Handshake.length:
            buf = await asyncio.wait_for(self.reader.read(
                PeerStreamIterator.CHUNK_SIZE), 60)

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

        self.writer.write(Handshake(self.info_hash, self.peer_id).encode())
        await self.writer.drain()

        return buf

    def close(self):
        if self.writer is not None:
            self.writer.close()
