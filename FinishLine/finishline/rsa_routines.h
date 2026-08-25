
#pragma once

int rsa_init(void);
const uint8_t* public_key_pem();
void rsa_pub_encrypt(unsigned char* to_encrypt, size_t to_encrypt_len, unsigned char* encrypted, size_t encrypted_size, size_t* encrypted_len);
void rsa_priv_dec(unsigned char* encrypted, size_t encrypted_len, unsigned char* decrypted, size_t decrypted_size, size_t* decrypted_len);
