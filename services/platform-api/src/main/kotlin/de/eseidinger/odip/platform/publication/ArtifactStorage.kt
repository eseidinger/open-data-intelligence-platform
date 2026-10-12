package de.eseidinger.odip.platform.publication

import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Component
import java.util.UUID

interface ArtifactStorage {
    fun read(publication: UUID, artifact: String): ByteArray?
    fun put(publication: UUID, artifact: String, bytes: ByteArray)
}

@Component
class PostgresArtifactStorage(private val jdbc: JdbcTemplate) : ArtifactStorage {
    override fun read(publication: UUID, artifact: String): ByteArray? = jdbc.query(
        "SELECT payload FROM publication_artifact WHERE publication_id=? AND artifact_id=?",
        { row, _ -> row.getBytes(1) }, publication, artifact).firstOrNull()

    override fun put(publication: UUID, artifact: String, bytes: ByteArray) {
        jdbc.update("INSERT INTO publication_artifact VALUES (?,?,?,?)", publication, artifact, bytes, sha256(bytes))
    }
}
