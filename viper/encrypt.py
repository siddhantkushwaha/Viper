import os
import random

import requests


class Util:
    def generate_str_key(self):
        CHARSET = b"""!"#$%&'()*+,-.0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~"""
        char_list = list(CHARSET)
        random.shuffle(char_list)

        key = []
        for i in range(128):
            idx = CHARSET.index(i) if i in CHARSET else -1
            key.append(char_list[idx] if idx > -1 else i)

        return bytes(key)

    def generate_key(self):
        byts = list(range(256))
        random.shuffle(byts)
        return bytes(byts)

    def download_key(self, path, url):
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as fp:
                fp.write(requests.get(url).content)

    def get_keys(self, path):
        with open(path, 'rb') as f:
            key = f.read()
        encryption_key = list(key)
        decryption_key = [encryption_key.index(i) for i in range(len(encryption_key))]
        return encryption_key, decryption_key


class Encrypt:

    def __init__(self, identifier, keys_dir='.'):
        util = Util()

        self.prefix = identifier

        self.keys_path = os.path.join(keys_dir, 'keys')

        self.data_key_name = 'key_data'
        self.str_key_name = 'key_str'

        self.data_keys = util.get_keys(os.path.join(self.keys_path, self.data_key_name))
        self.path_keys = util.get_keys(os.path.join(self.keys_path, self.str_key_name))

    def _encrypt(self, key, data: bytes) -> bytes:
        encrypted_data = []
        for byt in list(data):
            encrypted_data.append(key[byt])
        return bytes(encrypted_data)

    def _decrypt(self, key, data: bytes) -> bytes:
        decrypted_data = []
        for byt in list(data):
            decrypted_data.append(key[byt])
        return bytes(decrypted_data)

    def is_already_encrypted(self, path: str) -> bool:
        return self._decrypt(self.path_keys[1], path.encode()).decode().startswith(self.prefix)

    def encrypt_path(self, path: str) -> str:
        path_comps = path.split(os.path.sep)
        enc_path_comps = []
        for path_comp in path_comps:
            enc_path_comps.append(path_comp if self.is_already_encrypted(path_comp) else
                                  self._encrypt(self.path_keys[0], f'{self.prefix}{path_comp}'.encode()).decode())
        return os.path.sep.join(enc_path_comps)

    def decrypt_path(self, path: str) -> str:
        path_comps = path.split(os.path.sep)
        dec_path_comps = []
        for path_comp in path_comps:
            dec_path_comp = self._decrypt(self.path_keys[1], path_comp.encode()).decode()
            dec_path_comps.append(
                dec_path_comp[len(self.prefix):] if dec_path_comp.startswith(self.prefix) else path_comp)
        return os.path.sep.join(dec_path_comps)

    def encrypt_data(self, content: bytes) -> bytes:
        return self._encrypt(self.data_keys[0], content)

    def decrypt_data(self, content: bytes) -> bytes:
        return self._decrypt(self.data_keys[1], content)

    def process_file(self, src_pt, dest_pt, method):
        os.makedirs(os.path.dirname(dest_pt), exist_ok=True)

        if os.path.exists(dest_pt) and os.stat(src_pt).st_size == os.stat(dest_pt).st_size:
            print('Skipped.')
            return

        fp1 = open(src_pt, 'rb')
        fp2 = open(dest_pt, 'wb')

        chunk_size = 4 * 1024 * 1024

        while True:
            data = fp1.read(chunk_size)
            if not data:
                break

            if method == 1:
                fp2.write(self.encrypt_data(data))
            else:
                fp2.write(self.decrypt_data(data))

        fp1.close()
        fp2.close()

    def encrypt_file(self, src_pt, dest_pt):
        self.process_file(src_pt, dest_pt, method=1)

    def decrypt_file(self, src_pt, dest_pt):
        self.process_file(src_pt, dest_pt, method=2)
