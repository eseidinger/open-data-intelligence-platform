package de.eseidinger.odip.platform.publication

import de.eseidinger.odip.platform.storage.ObjectReference
import de.eseidinger.odip.platform.storage.ObjectStore
import de.eseidinger.odip.platform.storage.storageFailure
import org.springframework.beans.factory.ObjectProvider
import org.springframework.beans.factory.annotation.Value
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Component
import java.util.UUID

interface ArtifactStorage {
    fun read(publication: UUID, artifact: String): ByteArray?
    fun put(publication: UUID, artifact: String, bytes: ByteArray)
    fun readRaw(id: UUID): ByteArray?
    fun putRaw(id: UUID, bytes: ByteArray)
    fun externalWrites(): Boolean
}

@Component
class RoutedArtifactStorage(
    private val jdbc: JdbcTemplate,
    private val stores: ObjectProvider<ObjectStore>,
    @Value("\${odip.artifact-storage.backend:postgres}") private val backend: String,
) : ArtifactStorage {
    init {
        require(backend in setOf("postgres", "s3")) { "Unsupported artifact storage backend" }
    }

    override fun externalWrites() = backend == "s3"
    private fun store() = stores.ifAvailable ?: throw storageFailure("storage_not_configured")
    fun publicationKey(publication: UUID, artifact: String) = "publication/$publication/$artifact"
    fun rawKey(id: UUID) = "raw/$id"

    private fun reference(key: String): ObjectReference? = jdbc.query(
        "SELECT bucket,object_key,version_id,sha256,content_length FROM artifact_object WHERE storage_id=?",
        { row, _ -> ObjectReference(row.getString(1), row.getString(2), row.getString(3), row.getString(4), row.getLong(5)) },
        key,
    ).firstOrNull()

    private fun verified(bytes: ByteArray, digest: String, length: Long): ByteArray {
        if (bytes.size.toLong() != length || sha256(bytes) != digest) throw storageFailure("storage_integrity_failed")
        return bytes
    }

    private fun read(key: String, bytes: ByteArray?, digest: String, length: Long): ByteArray {
        val external = reference(key)
        // Never silently fall back to a retained database copy on S3 failure.
        val content = if (external == null) bytes ?: throw storageFailure("storage_content_missing") else store().read(external)
        return verified(content, digest, length)
    }

    override fun read(publication: UUID, artifact: String): ByteArray? = jdbc.query(
        "SELECT payload,sha256,COALESCE(content_length,octet_length(payload)) FROM publication_artifact WHERE publication_id=? AND artifact_id=?",
        { row, _ -> read(publicationKey(publication, artifact), row.getBytes(1), row.getString(2), row.getLong(3)) },
        publication,
        artifact,
    ).firstOrNull()

    override fun put(publication: UUID, artifact: String, bytes: ByteArray) {
        jdbc.update("INSERT INTO publication_artifact(publication_id,artifact_id,payload,sha256,content_length) VALUES (?,?,?,?,?)", publication, artifact, if (externalWrites()) null else bytes, sha256(bytes), bytes.size.toLong())
        if (externalWrites()) attach(publicationKey(publication, artifact), null, publication, artifact, bytes)
    }

    override fun readRaw(id: UUID): ByteArray? = jdbc.query(
        "SELECT payload,checksum_sha256,content_length FROM raw_artifact WHERE id=?",
        { row, _ -> read(rawKey(id), row.getBytes(1), row.getString(2), row.getLong(3)) },
        id,
    ).firstOrNull()

    override fun putRaw(id: UUID, bytes: ByteArray) {
        if (externalWrites()) attach(rawKey(id), id, null, null, bytes)
    }

    fun migrate(key: String, raw: UUID?, publication: UUID?, artifact: String?, bytes: ByteArray, apply: Boolean): Map<String, Any> {
        if (!externalWrites()) throw storageFailure("storage_not_configured")
        store().check()
        if (bytes.size > 10485760) throw storageFailure("storage_reference_invalid")
        val retained = jdbc.queryForObject("SELECT EXISTS(SELECT 1 FROM raw_artifact WHERE id=? AND payload IS NOT NULL) OR EXISTS(SELECT 1 FROM publication_artifact WHERE publication_id=? AND artifact_id=? AND payload IS NOT NULL)", Boolean::class.java, raw, publication, artifact) == true
        val previous = reference(key)
        if (previous != null) {
            verified(store().read(previous), sha256(bytes), bytes.size.toLong())
            return mapOf("status" to "already_migrated", "sha256" to sha256(bytes), "contentLength" to bytes.size, "postgresCopyRetained" to retained)
        }
        if (apply) attach(key, raw, publication, artifact, bytes)
        return mapOf("status" to if (apply) "migrated" else "ready", "sha256" to sha256(bytes), "contentLength" to bytes.size, "postgresCopyRetained" to retained)
    }

    private fun attach(key: String, raw: UUID?, publication: UUID?, artifact: String?, bytes: ByteArray) {
        val ref = store().put(bytes)
        verified(store().read(ref), sha256(bytes), bytes.size.toLong())
        jdbc.update("INSERT INTO artifact_object(storage_id,raw_artifact_id,publication_id,artifact_id,bucket,object_key,version_id,sha256,content_length) VALUES (?,?,?,?,?,?,?,?,?)", key, raw, publication, artifact, ref.bucket, ref.key, ref.version, ref.digest, ref.length)
    }
}
