import asyncio
from src.peer import PeerConnection, PeerState


class PeersManager:
    def __init__(self, queue, info_hash, peer_id, piece_manager, on_block_cb=None,
                 max_download_peers=35, max_upload_peers=35):
        self.max_download_peers = max_download_peers
        self.max_upload_peers = max_upload_peers
        self.download_peers = []
        self.upload_peers = []
        self.peer_id = peer_id
        self.peers = queue
        self.info_hash = info_hash
        self.piece_manager = piece_manager
        self.on_block_cb = on_block_cb

    async def start_download(self):
        await self.update_download()

    async def start_upload(self):
        server = await asyncio.start_server(self.new_connection_handle, '0.0.0.0', 6889)
        addr = server.sockets[0].getsockname()
        async with server:
            await server.serve_forever()

    async def new_connection_handle(self, reader, writer):
        peer = PeerConnection(reader, writer, self.info_hash, self.peer_id, self.piece_manager, self.on_block_cb,
                              self.update_upload)
        my_state = [PeerState.Interested, PeerState.Choke]
        peer_state = [PeerState.Choke]
        peer_future = asyncio.ensure_future(peer.start(my_state, peer_state))
        self.upload_peers.append(peer)

    async def update_download(self):
        for i, peer in enumerate(self.download_peers):
            if PeerState.Stopped in peer.my_state:
                del self.download_peers[i]

        while len(self.download_peers) < self.max_download_peers:
            ip, port = await self.peers.get()
            reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), 30)
            peer = PeerConnection(reader, writer, self.info_hash, self.peer_id, self.piece_manager, self.on_block_cb,
                                  self.update_download)
            my_state = [PeerState.Interested, PeerState.Choke]
            peer_state = [PeerState.Choke]
            peer_future = asyncio.ensure_future(peer.start(my_state, peer_state))
            self.download_peers.append(peer)

    async def update_upload(self):
        for i, peer in enumerate(self.upload_peers):
            if PeerState.Stopped in peer.my_state:
                del self.upload_peers[i]
