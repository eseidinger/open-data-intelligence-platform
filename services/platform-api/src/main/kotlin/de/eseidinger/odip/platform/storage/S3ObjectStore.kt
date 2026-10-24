package de.eseidinger.odip.platform.storage

import de.eseidinger.odip.platform.publication.PublicationError
import de.eseidinger.odip.platform.publication.sha256
import org.springframework.beans.factory.annotation.Value
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.stereotype.Component
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider
import software.amazon.awssdk.core.sync.RequestBody
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.s3.S3Client
import java.net.URI
import java.time.Duration
import java.util.UUID

// Only the API receives the platform's resource-scoped S3 binding. The worker
// continues to use the authorized application API and receives no store secrets.
@Configuration
@ConditionalOnProperty(name = ["odip.artifact-storage.backend"], havingValue = "s3")
class S3Configuration {
    @Bean(destroyMethod = "close")
    fun s3Client(@Value("\${AWS_ENDPOINT_URL_S3}") endpoint: String, @Value("\${AWS_DEFAULT_REGION:us-east-1}") region: String): S3Client {
        val uri = URI.create(endpoint)
        require(uri.scheme in setOf("http", "https") && uri.host != null && uri.userInfo == null && uri.query == null && uri.fragment == null) { "Invalid S3 endpoint configuration" }
        return S3Client.builder().endpointOverride(uri).region(Region.of(region))
            .credentialsProvider(DefaultCredentialsProvider.builder().build())
            .forcePathStyle(true)
            .httpClientBuilder(UrlConnectionHttpClient.builder().connectionTimeout(Duration.ofSeconds(5)).socketTimeout(Duration.ofSeconds(30)))
            .overrideConfiguration { it.apiCallTimeout(Duration.ofSeconds(60)).apiCallAttemptTimeout(Duration.ofSeconds(30)) }
            .build()
    }
}

data class ObjectReference(val bucket: String, val key: String, val version: String, val digest: String, val length: Long)

interface ObjectStore {
    fun put(bytes: ByteArray): ObjectReference
    fun read(reference: ObjectReference): ByteArray
    fun delete(reference: ObjectReference)
    fun check()
}

@Component
@ConditionalOnProperty(name = ["odip.artifact-storage.backend"], havingValue = "s3")
class S3ObjectStore(private val client: S3Client, @Value("\${S3_BUCKET}") private val bucket: String) : ObjectStore {
    override fun put(bytes: ByteArray): ObjectReference = safe {
        if (bytes.size > 10485760) throw storageFailure("storage_reference_invalid")
        check()
        val key = "odip/artifacts/${UUID.randomUUID()}"
        val response = client.putObject({ it.bucket(bucket).key(key).contentLength(bytes.size.toLong()) }, RequestBody.fromBytes(bytes))
        val version = response.versionId()
        if (version.isNullOrBlank() || version == "null") throw storageFailure("storage_versioning_required")
        ObjectReference(bucket, key, version, sha256(bytes), bytes.size.toLong())
    }

    override fun read(reference: ObjectReference): ByteArray = safe {
        if (reference.bucket != bucket || reference.version.isBlank() || reference.version == "null" || reference.length !in 0..10485760) throw storageFailure("storage_reference_invalid")
        client.getObject { it.bucket(bucket).key(reference.key).versionId(reference.version) }.use { stream ->
            if (stream.response().contentLength() != reference.length || stream.response().versionId() != reference.version) throw storageFailure("storage_integrity_failed")
            val bytes = stream.readNBytes(reference.length.toInt() + 1)
            if (bytes.size.toLong() != reference.length || sha256(bytes) != reference.digest) throw storageFailure("storage_integrity_failed")
            bytes
        }
    }

    override fun check() = safe {
        if (client.getBucketVersioning { it.bucket(bucket) }.statusAsString() != "Enabled") throw storageFailure("storage_versioning_required")
    }

    override fun delete(reference: ObjectReference) = safe {
        if (reference.bucket != bucket || reference.version.isBlank() || reference.version == "null") throw storageFailure("storage_reference_invalid")
        client.deleteObject { it.bucket(bucket).key(reference.key).versionId(reference.version) }
        Unit
    }

    private fun <T> safe(action: () -> T): T = try {
        action()
    } catch (error: PublicationError) {
        throw error
    } catch (_: Exception) {
        // SDK errors can contain credentials, endpoints and response payloads.
        throw storageFailure("storage_unavailable")
    }
}

fun storageFailure(code: String) = PublicationError(503, code, "Artifact storage could not complete the verified operation")
