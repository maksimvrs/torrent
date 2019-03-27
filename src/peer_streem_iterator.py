import asyncio
import logging
from concurrent.futures import CancelledError

from src.peer_protocol import *


class PeerStreamIterator:
    """
    The `PeerStreamIterator` is an async iterator that continuously reads from
    the given stream reader and tries to parse valid BitTorrent messages from
    off that stream of bytes.

    If the connection is dropped, something fails the iterator will abort by
    raising the `StopAsyncIteration` error ending the calling iteration.
    """
    CHUNK_SIZE = 10 * 1024

    def __init__(self, reader, initial: bytes = None):
        self.reader = reader
        self.buffer = initial if initial else b''

    async def __aiter__(self):
        return self

    async def __anext__(self):
        # Read data from the socket. When we have enough data to parse, parse
        # it and return the message. Until then keep reading from stream
        while True:
            try:
                if len(self.buffer) >= 4:
                    message_length = struct.unpack('>I', self.buffer[0:4])[0]
                    if message_length == 0:
                        if len(self.buffer) > 4:
                            self.buffer = self.buffer[4:]
                        else:
                            self.buffer = b''
                        return KeepAlive()
                    if len(self.buffer) >= message_length + 4:
                        message = self.parse(
                            self.buffer[:message_length + 5], message_length)
                        if len(self.buffer) > message_length + 4:
                            self.buffer = self.buffer[message_length + 4:]
                        else:
                            self.buffer = b''
                        if message:
                            return message
                        raise StopAsyncIteration
                self.buffer += await asyncio.wait_for(
                    self.reader.read(PeerStreamIterator.CHUNK_SIZE), 15)

            except ConnectionResetError:
                logging.debug('Connection closed by peer')
                raise StopAsyncIteration
            except CancelledError:
                raise StopAsyncIteration
            except asyncio.TimeoutError:
                return None
            except Exception:
                logging.exception('Error when iterating over stream!')
                raise StopAsyncIteration
        raise StopAsyncIteration

    def parse(self, message, message_length):
        """
        Tries to parse protocol messages if there is enough bytes read in the
        buffer.

        :return The parsed message, or None if no message could be parsed
        """
        # Each message is structured as:
        #     <length prefix><message ID><payload>
        #
        # The `length prefix` is a four byte big-endian value
        # The `message ID` is a decimal byte
        # The `payload` is the value of `length prefix`
        #
        # The message length is not part of the actual length. So another
        # 4 bytes needs to be included when slicing the buffer.

        if message_length == 0:
            return KeepAlive()

        message_id = struct.unpack('>b', self.buffer[4:5])[0]

        if message_id is PeerMessage.BitField:
            return BitField.decode(message)
        elif message_id is PeerMessage.Interested:
            return Interested()
        elif message_id is PeerMessage.NotInterested:
            return NotInterested()
        elif message_id is PeerMessage.Choke:
            return Choke()
        elif message_id is PeerMessage.Unchoke:
            return Unchoke()
        elif message_id is PeerMessage.Have:
            return Have.decode(message)
        elif message_id is PeerMessage.Piece:
            return Piece.decode(message)
        elif message_id is PeerMessage.Request:
            return Request.decode(message)
        elif message_id is PeerMessage.Cancel:
            return Cancel.decode(message)
        return None
