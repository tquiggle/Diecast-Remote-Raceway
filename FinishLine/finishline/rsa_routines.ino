#include <mbedtls/pk.h>
#include <mbedtls/ctr_drbg.h>
#include <mbedtls/entropy.h>
#include <mbedtls/ctr_drbg.h>
#include <mbedtls/rsa.h>

#define KEY_SIZE 2048
#define EXPONENT 65537
#define PEM_BUFFER_SIZE 500

mbedtls_pk_context pk;
mbedtls_entropy_context entropy;
mbedtls_ctr_drbg_context ctr_drbg;

uint8_t pubKeyPem[PEM_BUFFER_SIZE];

void cleanup() {

  mbedtls_pk_free(&pk);
  mbedtls_ctr_drbg_free(&ctr_drbg);
  mbedtls_entropy_free(&entropy);
  Serial.flush();
}

int rsa_init(void) {
  int ret = true;

  const char* pers = "Diecast Remote Raceway";
  char error_str[255];

  //  mbedtls_rsa_init(&rsa);
  mbedtls_pk_init(&pk);
  mbedtls_entropy_init(&entropy);
  mbedtls_ctr_drbg_init(&ctr_drbg);

  // 1. Seed the random number generator
  Serial.printf("Seeding the random number generator...\n");
  if ((ret = mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy,
                                   (const unsigned char*)pers,
                                   strlen(pers)))
      != 0) {
    mbedtls_strerror(ret, error_str, sizeof(error_str));
    printf("Failed! mbedtls_ctr_drbg_seed returned -0x%04x: %s\n", -ret, error_str);
    cleanup();
    return false;
  }

  // Generate the RSA key pair
  Serial.printf("Generating RSA key pair (key size %d, exponent %d)...\n", KEY_SIZE, EXPONENT);
  Serial.flush();
  if ((ret = mbedtls_pk_setup(&pk, mbedtls_pk_info_from_type(MBEDTLS_PK_RSA))) != 0) {
    mbedtls_strerror(ret, error_str, sizeof(error_str));
    Serial.printf("Failed! mbedtls_pk_setup returned -0x%04x: %s\n", -ret, error_str);
    cleanup();
    return false;
  }

  if ((ret = mbedtls_rsa_gen_key(mbedtls_pk_rsa(pk), mbedtls_ctr_drbg_random, &ctr_drbg,
                                 KEY_SIZE, EXPONENT))
      != 0) {
    mbedtls_strerror(ret, error_str, sizeof(error_str));
    printf("Failed! mbedtls_rsa_gen_key returned -0x%04x\n: %s", -ret, error_str);
    cleanup();
    return false;
  }


  // Verify the context actually holds an RSA key before extraction
  if (mbedtls_pk_get_type(&pk) == MBEDTLS_PK_RSA) {
      // Extract the low-level RSA context pointer
      mbedtls_rsa_context *rsa_ctx = mbedtls_pk_rsa(pk);
      
      if (rsa_ctx != NULL) {
          mbedtls_rsa_set_padding(rsa_ctx, MBEDTLS_RSA_PKCS_V21, MBEDTLS_MD_SHA256);
      }
  }

  Serial.println("Saving pub key as PEM string");
  Serial.flush();

  if (mbedtls_pk_write_pubkey_pem(&pk, pubKeyPem, PEM_BUFFER_SIZE) != 0) {
    Serial.println("write public key to string failed");
    Serial.flush();
    cleanup();
    return false;
  }

  Serial.println("key=");
  Serial.println((char*)pubKeyPem);

  Serial.println("rsa_init(): returning true");
  Serial.flush();
  return true;
}

void rsa_pub_encrypt(unsigned char* to_encrypt, size_t to_encrypt_len, unsigned char* encrypted, size_t encrypted_size, size_t* encrypted_len) {
  int ret = 0;

  printf("rsa_pub_encrypt(): Generating the encrypted value");
  fflush(stdout);
  ret = mbedtls_pk_encrypt(&pk, to_encrypt, to_encrypt_len, encrypted, encrypted_len, encrypted_size, mbedtls_ctr_drbg_random, &ctr_drbg);

  if (ret != 0) {
    printf("rsa_pub_encrypt(): failed\n  mbedtls_pk_encrypt returned -0x%04x\n", -ret);
    // goto exit;
  } else {
    Serial.printf("rsa_pub_encrypt(): Encrypt success!\n");
  }
}


void rsa_priv_dec(unsigned char* encrypted, size_t encrypted_len, unsigned char* decrypted, size_t decrypted_size, size_t* decrypted_len) {
  int ret = 0;

  printf("\n  . Generating the decrypted value");
  fflush(stdout);

  if ((ret = mbedtls_pk_decrypt(&pk, encrypted, encrypted_len, decrypted, decrypted_len, decrypted_size, mbedtls_ctr_drbg_random, &ctr_drbg)) != 0) {
    Serial.printf(" failed\n  ! mbedtls_pk_decrypt returned -0x%04x\n", -ret);
    //Serial.printf(" failed\n  ! mbedtls_pk_decrypt returned %d\n", ret);
  }
}

const uint8_t* public_key_pem() {
  return pubKeyPem;
}


// End of file.
